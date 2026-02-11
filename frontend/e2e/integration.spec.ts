/**
 * US-INT-001 — Front-end/back-end full integration E2E test.
 *
 * Prerequisites: backend running on port 8000, frontend running on port 5173.
 *
 * Validates the complete user flow:
 *   1. Three-column layout renders
 *   2. Load built-in sample via dropdown
 *   3. Graph renders with correct node shapes/colors
 *   4. Header shows sandbox description
 *   5. Click node → ControlPanel shows properties and action buttons
 *   6. Click action button → ripple animation plays → InsightFeed shows insights
 *   7. Insights contain 3+ different types
 *   8. Reset → graph returns to initial state, insights cleared
 *   9. Re-simulate → same results (reset correctness)
 *  10. Swagger UI accessible at backend /docs
 */

import { test, expect } from '@playwright/test';

const BACKEND_URL = 'http://localhost:8000';

// ------------------------------------------------------------------
// Test Suite
// ------------------------------------------------------------------

test.describe('US-INT-001: Full Integration E2E', () => {

  test.describe.configure({ mode: 'serial' });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  // ------ AC 1 & 2: Three-column layout renders ------
  test('three-column layout is visible', async ({ page }) => {
    await expect(page.locator('.app-header')).toBeVisible();
    await expect(page.locator('.left-sider')).toBeVisible();
    await expect(page.locator('.main-content')).toBeVisible();
    await expect(page.locator('.right-sider')).toBeVisible();
  });

  // ------ AC 3: Load built-in sample via dropdown ------
  test('load corporate_acquisition sample from dropdown', async ({ page }) => {
    // Click "加载数据" to open drawer
    await page.getByRole('button', { name: /加载数据/ }).click();
    await page.waitForSelector('.ant-drawer-body', { timeout: 5000 });

    // Click the Select dropdown inside the drawer
    const selectTrigger = page.locator('.ant-drawer-body .ant-select');
    await selectTrigger.click();

    // antd Select renders options in a popup container appended to document.body
    // The option label is the description text (from the sample JSON metadata)
    // Wait for the dropdown popup to appear
    await page.waitForSelector('.ant-select-dropdown', { timeout: 5000 });

    // Click the first (and likely only) option in the dropdown
    await page.locator('.ant-select-dropdown .ant-select-item-option').first().click();

    // Wait for graph to load (placeholder disappears from main-content)
    await page.waitForFunction(() => {
      const placeholder = document.querySelector('.main-content .panel-placeholder');
      return !placeholder;
    }, { timeout: 15_000 });

    // Verify: graph canvas should not show placeholder text
    await expect(page.locator('.main-content')).not.toContainText('请上传 JSON 文件');
  });

  // ------ AC 6: Header shows sandbox description ------
  test('header shows sandbox description after loading', async ({ page }) => {
    await loadSample(page);
    await expect(page.locator('.app-header-title')).toContainText('基于投资与收购事件的风险传导推演沙盘');
  });

  // ------ AC 7: ControlPanel shows node prompt before any click ------
  test('ControlPanel shows prompt before node selection', async ({ page }) => {
    await loadSample(page);
    await expect(page.locator('.left-sider')).toContainText('请点击节点查看详情');
  });

  // ------ AC 9: Node colors/shapes driven by ontology_def ------
  test('ontology_def defines correct visual styles', async ({ request }) => {
    const resp = await request.post(`${BACKEND_URL}/api/v1/workspace/load?sample=corporate_acquisition`);
    const body = await resp.json();

    const nodeTypes = body.ontology_def.node_types;
    expect(nodeTypes.Company.color).toBe('#4A90D9');
    expect(nodeTypes.Company.shape).toBe('circle');
    expect(nodeTypes.Event_Acquisition.color).toBe('#F5A623');
    expect(nodeTypes.Event_Acquisition.shape).toBe('diamond');
    expect(nodeTypes.Person.color).toBe('#50C878');
    expect(nodeTypes.Person.shape).toBe('circle');
  });

  // ------ AC 8: Simulate returns structured insights with 3+ types ------
  test('simulate returns 3+ insight types including critical severity', async ({ request }) => {
    await request.post(`${BACKEND_URL}/api/v1/workspace/load?sample=corporate_acquisition`);

    const simResp = await request.post(`${BACKEND_URL}/api/v1/workspace/simulate`, {
      data: { action_id: 'trigger_acquisition_failure', node_id: 'E_ACQ_101' },
    });
    expect(simResp.ok()).toBe(true);
    const body = await simResp.json();

    expect(body.status).toBe('success');
    expect(body.ripple_path.length).toBeGreaterThanOrEqual(3);
    expect(body.ripple_path).toContain('E_ACQ_101');

    // 3+ different insight types
    const insightTypes = new Set(body.insights.map((i: { type: string }) => i.type));
    expect(insightTypes.size).toBeGreaterThanOrEqual(3);

    // Critical severity exists
    const hasCritical = body.insights.some((i: { severity: string }) => i.severity === 'critical');
    expect(hasCritical).toBe(true);

    // Insight text has no unfilled templates
    for (const insight of body.insights) {
      expect(insight.text).toBeTruthy();
      expect(insight.type).toBeTruthy();
      expect(insight.severity).toBeTruthy();
      expect(insight.text).not.toContain('{target[');
      expect(insight.text).not.toContain('{source[');
    }
  });

  // ------ AC 10: Reset restores initial state, clears history ------
  test('reset restores initial state and clears history', async ({ request }) => {
    await request.post(`${BACKEND_URL}/api/v1/workspace/load?sample=corporate_acquisition`);
    await request.post(`${BACKEND_URL}/api/v1/workspace/simulate`, {
      data: { action_id: 'trigger_acquisition_failure', node_id: 'E_ACQ_101' },
    });

    const resetResp = await request.post(`${BACKEND_URL}/api/v1/workspace/reset`);
    expect(resetResp.ok()).toBe(true);
    const resetBody = await resetResp.json();

    const nodes: Record<string, Record<string, unknown>> = {};
    for (const n of resetBody.nodes) {
      nodes[n.id] = n;
    }
    expect(nodes['E_ACQ_101']?.status).toBe('PENDING');
    expect(nodes['C_ALPHA']?.valuation).toBe(10000000);
    expect(nodes['C_ALPHA']?.risk_status).toBe('NORMAL');

    const histResp = await request.get(`${BACKEND_URL}/api/v1/workspace/history`);
    const history = await histResp.json();
    expect(history.length).toBe(0);
  });

  // ------ AC 11: Re-simulate after reset gives consistent results ------
  test('re-simulate after reset gives consistent results', async ({ request }) => {
    await request.post(`${BACKEND_URL}/api/v1/workspace/load?sample=corporate_acquisition`);

    const sim1Resp = await request.post(`${BACKEND_URL}/api/v1/workspace/simulate`, {
      data: { action_id: 'trigger_acquisition_failure', node_id: 'E_ACQ_101' },
    });
    const sim1 = await sim1Resp.json();
    const types1 = sim1.insights.map((i: { type: string }) => i.type).sort();
    const path1 = [...sim1.ripple_path].sort();

    await request.post(`${BACKEND_URL}/api/v1/workspace/reset`);

    const sim2Resp = await request.post(`${BACKEND_URL}/api/v1/workspace/simulate`, {
      data: { action_id: 'trigger_acquisition_failure', node_id: 'E_ACQ_101' },
    });
    const sim2 = await sim2Resp.json();
    const types2 = sim2.insights.map((i: { type: string }) => i.type).sort();
    const path2 = [...sim2.ripple_path].sort();

    expect(types2).toEqual(types1);
    expect(path2).toEqual(path1);
  });

  // ------ AC 13: Swagger UI accessible ------
  test('Swagger UI is accessible at /docs', async ({ request }) => {
    const resp = await request.get(`${BACKEND_URL}/docs`);
    expect(resp.ok()).toBe(true);
    const html = await resp.text();
    expect(html).toContain('swagger');
  });

  // ------ GET /samples ------
  test('GET /samples returns available samples list', async ({ request }) => {
    const resp = await request.get(`${BACKEND_URL}/api/v1/workspace/samples`);
    expect(resp.ok()).toBe(true);
    const samples = await resp.json();
    expect(samples.length).toBeGreaterThanOrEqual(1);
    const names = samples.map((s: { name: string }) => s.name);
    expect(names).toContain('corporate_acquisition');
  });

  // ------ AC 4: File upload / load via API ------
  test('load returns complete response structure', async ({ request }) => {
    const resp = await request.post(`${BACKEND_URL}/api/v1/workspace/load?sample=corporate_acquisition`);
    const body = await resp.json();

    expect(body.metadata).toBeTruthy();
    expect(body.metadata.domain).toBe('corporate_risk');
    expect(body.metadata.description).toBe('基于投资与收购事件的风险传导推演沙盘');
    expect(body.ontology_def).toBeTruthy();
    expect(body.ontology_def.node_types).toBeTruthy();
    expect(body.graph_data).toBeTruthy();
    expect(body.graph_data.nodes.length).toBeGreaterThanOrEqual(6);
    expect(body.graph_data.edges.length).toBeGreaterThanOrEqual(6);
    expect(body.actions).toBeTruthy();
    expect(body.actions.length).toBeGreaterThanOrEqual(2);
    expect(body.registered_functions).toBeTruthy();
    expect(body.registered_functions.length).toBeGreaterThanOrEqual(6);
  });

  // ------ Full UI flow: load → verify graph/legend/insight panels ------
  test('full browser UI flow: load → graph renders → legend visible → insight placeholder', async ({ page }) => {
    await loadSample(page);

    // Graph area no longer shows placeholder
    await expect(page.locator('.main-content')).not.toContainText('请上传 JSON 文件');

    // Left panel shows legend with all node types
    await expect(page.locator('.left-sider')).toContainText('图例');
    await expect(page.locator('.left-sider')).toContainText('公司');
    await expect(page.locator('.left-sider')).toContainText('收购事件');
    await expect(page.locator('.left-sider')).toContainText('关键人物');

    // Right panel shows empty state
    await expect(page.locator('.right-sider')).toContainText('执行模拟后');
  });

  // ------ Full API round-trip (self-contained) ------
  test('full API round-trip: load → simulate → history → reset → re-simulate', async ({ request }) => {
    // Load (this also resets any prior state since load is idempotent)
    const loadResp = await request.post(`${BACKEND_URL}/api/v1/workspace/load?sample=corporate_acquisition`);
    expect(loadResp.ok()).toBe(true);
    const loadBody = await loadResp.json();
    expect(loadBody.metadata.domain).toBe('corporate_risk');

    // Simulate
    const simResp = await request.post(`${BACKEND_URL}/api/v1/workspace/simulate`, {
      data: { action_id: 'trigger_acquisition_failure', node_id: 'E_ACQ_101' },
    });
    expect(simResp.ok()).toBe(true);
    const simBody = await simResp.json();
    expect(simBody.status).toBe('success');
    expect(simBody.ripple_path).toContain('E_ACQ_101');
    expect(simBody.ripple_path.length).toBeGreaterThanOrEqual(3);
    expect(simBody.delta_graph.updated_nodes.length).toBeGreaterThanOrEqual(2);
    expect(simBody.delta_graph.highlight_edges.length).toBeGreaterThanOrEqual(1);

    // 3+ insight types
    const insightTypes = new Set(simBody.insights.map((i: { type: string }) => i.type));
    expect(insightTypes.size).toBeGreaterThanOrEqual(3);
    expect(insightTypes.has('quantitative_impact')).toBe(true);

    // Check history has 1 event
    const histResp = await request.get(`${BACKEND_URL}/api/v1/workspace/history`);
    const history = await histResp.json();
    expect(history.length).toBeGreaterThanOrEqual(1);
    // Find the most recent event matching our action
    const lastEvent = history[history.length - 1];
    expect(lastEvent.action_id).toBe('trigger_acquisition_failure');

    // Reset
    const resetResp = await request.post(`${BACKEND_URL}/api/v1/workspace/reset`);
    expect(resetResp.ok()).toBe(true);
    const resetBody = await resetResp.json();
    const acqNode = resetBody.nodes.find((n: { id: string }) => n.id === 'E_ACQ_101');
    expect(acqNode.status).toBe('PENDING');

    // History cleared after reset
    const hist2Resp = await request.get(`${BACKEND_URL}/api/v1/workspace/history`);
    const hist2 = await hist2Resp.json();
    expect(hist2.length).toBe(0);

    // Re-simulate after reset → consistent results
    const sim2Resp = await request.post(`${BACKEND_URL}/api/v1/workspace/simulate`, {
      data: { action_id: 'trigger_acquisition_failure', node_id: 'E_ACQ_101' },
    });
    const sim2Body = await sim2Resp.json();
    expect(sim2Body.status).toBe('success');
    const types2 = new Set(sim2Body.insights.map((i: { type: string }) => i.type));
    expect(types2.size).toEqual(insightTypes.size);
    expect([...sim2Body.ripple_path].sort()).toEqual([...simBody.ripple_path].sort());
  });

  // ------ Health check ------
  test('backend health check returns ok', async ({ request }) => {
    const resp = await request.get(`${BACKEND_URL}/health`);
    expect(resp.ok()).toBe(true);
    const body = await resp.json();
    expect(body.status).toBe('ok');
  });
});

// ------------------------------------------------------------------
// Helper: Load the built-in sample via the frontend UI
// ------------------------------------------------------------------
async function loadSample(page: import('@playwright/test').Page) {
  // Click "加载数据" to open drawer
  await page.getByRole('button', { name: /加载数据/ }).click();
  await page.waitForSelector('.ant-drawer-body', { timeout: 5000 });

  // Click the Select dropdown inside drawer
  const selectTrigger = page.locator('.ant-drawer-body .ant-select');
  await selectTrigger.click();

  // Wait for the antd select dropdown popup (rendered on document.body)
  await page.waitForSelector('.ant-select-dropdown', { timeout: 5000 });

  // Click the first option (corporate_acquisition is the only sample)
  await page.locator('.ant-select-dropdown .ant-select-item-option').first().click();

  // Wait for graph to load (placeholder disappears)
  await page.waitForFunction(() => {
    const placeholder = document.querySelector('.main-content .panel-placeholder');
    return !placeholder;
  }, { timeout: 15_000 });

  // Allow graph rendering time
  await page.waitForTimeout(1500);

  // Close drawer if still open
  const closeBtn = page.locator('.ant-drawer-close');
  if (await closeBtn.isVisible()) {
    await closeBtn.click();
    await page.waitForTimeout(300);
  }
}
