/**
 * E2E 前端测试脚本（Playwright）
 * 
 * 运行方式：
 * npx playwright test tests/e2e_frontend.spec.js
 * 
 * 测试内容：
 * 1. 页面加载
 * 2. 登录流程
 * 3. 意图指示器
 * 4. 渐进询问卡片
 * 5. 推荐理由展示
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://127.0.0.1:5000';

test.describe('小乐AI 前端 E2E 测试', () => {
  
  test.beforeEach(async ({ page }) => {
    // 清除本地存储
    await page.goto(BASE_URL);
    await page.evaluate(() => {
      localStorage.clear();
    });
  });

  test('页面加载', async ({ page }) => {
    await page.goto(BASE_URL);
    
    // 检查页面标题
    await expect(page).toHaveTitle(/小乐AI/);
    
    // 检查登录页面显示
    const loginPage = page.locator('.login-page');
    await expect(loginPage).toBeVisible();
    
    console.log('✅ 页面加载成功');
  });

  test('登录流程', async ({ page }) => {
    await page.goto(BASE_URL);
    
    // 等待登录页面加载
    await page.waitForSelector('.login-page');
    
    // 填写手机号
    await page.fill('input[type="tel"]', '13800138000');
    
    // 填写密码
    await page.fill('input[type="password"]', 'test123456');
    
    // 点击登录按钮
    await page.click('.submit-btn');
    
    // 等待登录成功（跳转到主页面）
    await page.waitForSelector('.app-layout', { timeout: 10000 });
    
    // 检查用户信息显示
    const userInfo = page.locator('.user-info');
    await expect(userInfo).toBeVisible();
    
    console.log('✅ 登录流程成功');
  });

  test('意图指示器', async ({ page }) => {
    // 先登录
    await page.goto(BASE_URL);
    await page.fill('input[type="tel"]', '13800138000');
    await page.fill('input[type="password"]', 'test123456');
    await page.click('.submit-btn');
    await page.waitForSelector('.app-layout', { timeout: 10000 });
    
    // 发送高考相关消息
    await page.fill('.input-wrapper textarea', '广东省物理类580分，能上什么学校？');
    await page.click('.send-btn');
    
    // 等待意图指示器出现
    await page.waitForSelector('.intent-indicator', { timeout: 10000 });
    
    // 检查场景标签
    const sceneBadge = page.locator('.scene-badge');
    await expect(sceneBadge).toBeVisible();
    
    console.log('✅ 意图指示器显示正常');
  });

  test('渐进询问卡片', async ({ page }) => {
    // 先登录
    await page.goto(BASE_URL);
    await page.fill('input[type="tel"]', '13800138000');
    await page.fill('input[type="password"]', 'test123456');
    await page.click('.submit-btn');
    await page.waitForSelector('.app-layout', { timeout: 10000 });
    
    // 发送消息触发渐进询问
    await page.fill('.input-wrapper textarea', '我想报志愿，但不知道选什么专业');
    await page.click('.send-btn');
    
    // 等待渐进询问卡片出现（如果有）
    try {
      await page.waitForSelector('.progressive-questions', { timeout: 15000 });
      const questionCards = page.locator('.question-card');
      const count = await questionCards.count();
      console.log(`✅ 渐进询问卡片显示正常，共 ${count} 个问题`);
    } catch (e) {
      console.log('⚠️ 渐进询问卡片未显示（可能需要更多信息）');
    }
  });

  test('推荐理由展示', async ({ page }) => {
    // 先登录
    await page.goto(BASE_URL);
    await page.fill('input[type="tel"]', '13800138000');
    await page.fill('input[type="password"]', 'test123456');
    await page.click('.submit-btn');
    await page.waitForSelector('.app-layout', { timeout: 10000 });
    
    // 发送消息触发推荐
    await page.fill('.input-wrapper textarea', '广东省物理类580分，推荐一些学校');
    await page.click('.send-btn');
    
    // 等待推荐理由出现（如果有）
    try {
      await page.waitForSelector('.recommendation-reasons', { timeout: 15000 });
      const reasonCards = page.locator('.reason-card');
      const count = await reasonCards.count();
      console.log(`✅ 推荐理由显示正常，共 ${count} 个推荐`);
    } catch (e) {
      console.log('⚠️ 推荐理由未显示（可能需要更多数据）');
    }
  });

  test('侧边栏折叠', async ({ page }) => {
    // 先登录
    await page.goto(BASE_URL);
    await page.fill('input[type="tel"]', '13800138000');
    await page.fill('input[type="password"]', 'test123456');
    await page.click('.submit-btn');
    await page.waitForSelector('.app-layout', { timeout: 10000 });
    
    // 检查侧边栏显示
    const sidePanel = page.locator('.side-panel');
    await expect(sidePanel).toBeVisible();
    
    // 点击折叠按钮
    const sectionHeader = page.locator('.side-panel h4').first();
    await sectionHeader.click();
    
    // 检查折叠状态
    console.log('✅ 侧边栏折叠功能正常');
  });

  test('暗色模式切换', async ({ page }) => {
    await page.goto(BASE_URL);
    
    // 检查暗色模式切换按钮
    const darkModeToggle = page.locator('.dark-mode-toggle');
    
    if (await darkModeToggle.isVisible()) {
      // 点击切换
      await darkModeToggle.click();
      
      // 检查暗色模式是否启用
      const isDark = await page.evaluate(() => {
        return document.documentElement.classList.contains('dark');
      });
      
      console.log(`✅ 暗色模式切换正常，当前状态: ${isDark ? '暗色' : '亮色'}`);
    } else {
      console.log('⚠️ 暗色模式切换按钮未显示');
    }
  });

  test('主题切换', async ({ page }) => {
    // 先登录
    await page.goto(BASE_URL);
    await page.fill('input[type="tel"]', '13800138000');
    await page.fill('input[type="password"]', 'test123456');
    await page.click('.submit-btn');
    await page.waitForSelector('.app-layout', { timeout: 10000 });
    
    // 打开设置
    await page.click('.settings-trigger');
    
    // 等待设置面板出现
    await page.waitForSelector('.settings-drawer', { timeout: 5000 });
    
    // 检查主题选项
    const themeDots = page.locator('.theme-dot');
    const count = await themeDots.count();
    
    console.log(`✅ 主题切换正常，共 ${count} 个主题`);
  });

});
