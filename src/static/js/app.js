/**
 * app.js — 家庭财务管理系统公共交互脚本
 */

(function () {
  'use strict';

  // ── 侧边菜单 ──────────────────────────────────────────────
  const hamburgerBtn = document.getElementById('hamburger-btn');
  const sideMenu = document.getElementById('side-menu');
  const sideMenuOverlay = document.getElementById('side-menu-overlay');
  const sideMenuClose = document.getElementById('side-menu-close');
  const moreTabBtn = document.getElementById('more-tab-btn');

  function openMenu() {
    if (!sideMenu) return;
    sideMenu.classList.add('open');
    sideMenuOverlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeMenu() {
    if (!sideMenu) return;
    sideMenu.classList.remove('open');
    sideMenuOverlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  if (hamburgerBtn) hamburgerBtn.addEventListener('click', openMenu);
  if (moreTabBtn) moreTabBtn.addEventListener('click', openMenu);
  if (sideMenuOverlay) sideMenuOverlay.addEventListener('click', closeMenu);
  if (sideMenuClose) sideMenuClose.addEventListener('click', closeMenu);

  // 点击菜单项后自动关闭
  if (sideMenu) {
    sideMenu.querySelectorAll('.side-menu-item').forEach(function (item) {
      item.addEventListener('click', closeMenu);
    });
  }

  // ── Toast 自动消失 ─────────────────────────────────────────
  document.querySelectorAll('.toast[data-auto-dismiss="true"]').forEach(function (toast) {
    setTimeout(function () {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      setTimeout(function () { toast.remove(); }, 300);
    }, 3000);
  });

  // Toast 手动关闭
  document.querySelectorAll('.toast-close').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var toast = btn.closest('.toast');
      if (toast) {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(function () { toast.remove(); }, 300);
      }
    });
  });

  // ── 删除确认弹窗 ──────────────────────────────────────────
  var confirmModal = document.getElementById('confirm-modal');
  var confirmMessage = document.getElementById('confirm-modal-message');
  var confirmBtn = document.getElementById('confirm-modal-confirm');
  var cancelBtn = document.getElementById('confirm-modal-cancel');
  var pendingAction = null;

  function showConfirm(message, action) {
    if (!confirmModal) return;
    confirmMessage.textContent = message;
    pendingAction = action;
    confirmModal.classList.add('open');
  }

  function hideConfirm() {
    if (!confirmModal) return;
    confirmModal.classList.remove('open');
    pendingAction = null;
  }

  if (cancelBtn) cancelBtn.addEventListener('click', hideConfirm);
  if (confirmModal) {
    confirmModal.querySelector('.confirm-modal-overlay').addEventListener('click', hideConfirm);
  }
  if (confirmBtn) {
    confirmBtn.addEventListener('click', function () {
      if (pendingAction) pendingAction();
      hideConfirm();
    });
  }

  // 拦截所有 [data-confirm-delete] 点击
  document.addEventListener('click', function (e) {
    var trigger = e.target.closest('[data-confirm-delete]');
    if (!trigger) return;
    e.preventDefault();

    var message = trigger.getAttribute('data-confirm-message') || '确定要删除吗？';
    var url = trigger.getAttribute('data-url');
    var form = trigger.closest('form');

    showConfirm(message, function () {
      if (url) {
        window.location.href = url;
      } else if (form) {
        form.submit();
      }
    });
  });

  // ── 表单提交 loading ──────────────────────────────────────
  document.querySelectorAll('form[data-loading]').forEach(function (form) {
    form.addEventListener('submit', function () {
      var btn = form.querySelector('button[type="submit"], input[type="submit"]');
      if (btn && !btn.disabled) {
        btn.disabled = true;
        btn.dataset.originalText = btn.textContent;
        btn.textContent = '处理中...';
      }
    });
  });

  // ── 日期显示 ──────────────────────────────────────────────
  var dateEl = document.getElementById('current-date');
  if (dateEl) {
    var now = new Date();
    var options = { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' };
    dateEl.textContent = now.toLocaleDateString('zh-CN', options);
  }

  // ── 财务数据隐藏（小眼睛） ──────────────────────────────────
  var HIDDEN_KEY = 'ff_data_hidden';
  var isHidden = localStorage.getItem(HIDDEN_KEY) !== '0'; // 默认隐藏

  // 需要隐藏金额的选择器（覆盖所有页面）
  var AMOUNT_SELECTORS = '.stat-value, .dash-stat-value, .asset-row-value, .amount-hide';

  // 插入眼睛按钮的锚点：.stats-bar（子页面）或 .dashboard-card:first-child .dashboard-card-header（首页仪表盘）
  var eyeAnchors = [];
  var statsBars = document.querySelectorAll('.stats-bar');
  statsBars.forEach(function(bar) {
    eyeAnchors.push({ target: bar, mode: 'before' });
  });
  // 首页仪表盘：在第一个卡片头部插入
  var dashHeader = document.querySelector('.dashboard-card .dashboard-card-header');
  if (dashHeader && eyeAnchors.length === 0) {
    eyeAnchors.push({ target: dashHeader, mode: 'inside' });
  }

  eyeAnchors.forEach(function(anchor) {
    var eyeBtn = document.createElement('button');
    eyeBtn.className = 'eye-toggle';
    eyeBtn.type = 'button';
    eyeBtn.innerHTML = isHidden ? '🙈' : '👁';
    eyeBtn.title = isHidden ? '显示数据' : '隐藏数据';
    eyeBtn.addEventListener('click', function() {
      isHidden = !isHidden;
      localStorage.setItem(HIDDEN_KEY, isHidden ? '1' : '0');
      applyDataVisibility();
      document.querySelectorAll('.eye-toggle').forEach(function(btn) {
        btn.innerHTML = isHidden ? '🙈' : '👁';
        btn.title = isHidden ? '显示数据' : '隐藏数据';
      });
    });

    if (anchor.mode === 'inside') {
      // 插入到 header 内部右侧
      eyeBtn.style.marginLeft = 'auto';
      anchor.target.appendChild(eyeBtn);
    } else {
      // 插入到 stats-bar 上方
      var wrapper = document.createElement('div');
      wrapper.style.cssText = 'display:flex;justify-content:flex-end;margin-bottom:-8px;';
      wrapper.appendChild(eyeBtn);
      anchor.target.parentNode.insertBefore(wrapper, anchor.target);
    }
  });

  function applyDataVisibility() {
    document.querySelectorAll(AMOUNT_SELECTORS).forEach(function(el) {
      if (isHidden) {
        if (!el.dataset.original) el.dataset.original = el.textContent;
        el.textContent = '****';
      } else {
        if (el.dataset.original) el.textContent = el.dataset.original;
      }
    });
  }

  // 暴露给页面内联脚本，用于 JS 动态赋值后重新隐藏
  window.ffReapplyHide = function() {
    // 先清除缓存的 original，重新读取当前值
    document.querySelectorAll(AMOUNT_SELECTORS).forEach(function(el) {
      delete el.dataset.original;
    });
    if (isHidden) applyDataVisibility();
  };

  if (isHidden) applyDataVisibility();

  // ── AI 抽屉全局函数 ──────────────────────────────────────────
  window.aiDrawer = {
    _currentRefreshFn: null,
    _currentType: null,
    _lastUrl: null,

    open: function(title, adviceType) {
      var drawer = document.getElementById('ai-drawer');
      var overlay = document.getElementById('ai-drawer-overlay');
      if (!drawer || !overlay) return;
      document.getElementById('ai-drawer-title').textContent = title || 'AI 分析';
      this._currentType = adviceType || null;
      drawer.classList.add('open');
      overlay.classList.add('open');
      document.body.style.overflow = 'hidden';

      var historyLink = document.getElementById('ai-drawer-history');
      if (adviceType) {
        historyLink.href = '/advisor/history?type=' + adviceType;
        historyLink.style.display = '';
      } else {
        historyLink.style.display = 'none';
      }
    },

    close: function() {
      var drawer = document.getElementById('ai-drawer');
      var overlay = document.getElementById('ai-drawer-overlay');
      if (drawer) drawer.classList.remove('open');
      if (overlay) overlay.classList.remove('open');
      document.body.style.overflow = '';
      this._currentRefreshFn = null;
      // 清除转投按钮（如果有）
      var transferBtn = document.getElementById('btn-transfer-from-drawer');
      if (transferBtn) transferBtn.remove();
    },

    setLoading: function() {
      document.getElementById('ai-drawer-body').innerHTML = '<div class="ai-drawer-loading"><span class="loading-text">🤖 AI 分析中，请稍候...</span></div>';
      document.getElementById('ai-drawer-time').textContent = '';
      document.getElementById('ai-drawer-refresh').style.display = 'none';
    },

    setContent: function(html, generatedAt, fromCache, refreshFn) {
      document.getElementById('ai-drawer-body').innerHTML = '<div class="advice-text">' + html + '</div>';
      var timeEl = document.getElementById('ai-drawer-time');
      timeEl.textContent = generatedAt ? '生成于 ' + generatedAt + (fromCache ? ' (缓存)' : '') : '';

      var refreshBtn = document.getElementById('ai-drawer-refresh');
      if (refreshFn) {
        this._currentRefreshFn = refreshFn;
        refreshBtn.style.display = '';
      }
    },

    setError: function(msg) {
      document.getElementById('ai-drawer-body').innerHTML = '<div class="ai-drawer-placeholder"><p class="error-text">' + (msg || '获取分析失败') + '</p></div>';
    },

    fetchAndShow: function(title, url, adviceType, refreshFn) {
      var self = this;
      // 所有分析都支持刷新，没传 refreshFn 就用自身参数重调
      var actualRefreshFn = refreshFn || function() {
        self.fetchAndShow(title, url, adviceType);
      };
      self.open(title, adviceType);
      self.setLoading();
      self._lastUrl = url;
      fetch(url).then(function(resp) {
        return resp.json();
      }).then(function(data) {
        if (typeof marked !== 'undefined') {
          self.setContent(marked.parse(data.advice), data.generated_at, data.from_cache, actualRefreshFn);
        } else {
          self.setContent('<pre style="white-space:pre-wrap;">' + data.advice + '</pre>', data.generated_at, data.from_cache, actualRefreshFn);
        }
      }).catch(function() {
        self.setError();
      });
    },

    // 强制刷新（跳过缓存）
    refreshCurrent: function() {
      if (!this._currentRefreshFn) return;
      // 拿到当前 URL 并加 ?refresh=1
      this._currentRefreshFn();
    }
  };

  // 绑定抽屉关闭事件
  var aiDrawerClose = document.getElementById('ai-drawer-close');
  var aiDrawerOverlay = document.getElementById('ai-drawer-overlay');
  var aiDrawerRefresh = document.getElementById('ai-drawer-refresh');

  if (aiDrawerClose) aiDrawerClose.addEventListener('click', function() { window.aiDrawer.close(); });
  if (aiDrawerOverlay) aiDrawerOverlay.addEventListener('click', function() { window.aiDrawer.close(); });
  if (aiDrawerRefresh) aiDrawerRefresh.addEventListener('click', function() {
    // 重新分析：加 ?refresh=1 跳过缓存
    var self = window.aiDrawer;
    if (!self._currentRefreshFn) return;
    var origFn = self._currentRefreshFn;
    // 包装一层：给 URL 加 refresh=1
    self.setLoading();
    // 从 _lastUrl 取 URL，加 refresh 参数
    var url = self._lastUrl;
    if (url) {
      var sep = url.indexOf('?') >= 0 ? '&' : '?';
      fetch(url + sep + 'refresh=1').then(function(resp) {
        return resp.json();
      }).then(function(data) {
        if (typeof marked !== 'undefined') {
          self.setContent(marked.parse(data.advice), data.generated_at, data.from_cache, origFn);
        } else {
          self.setContent('<pre style="white-space:pre-wrap;">' + data.advice + '</pre>', data.generated_at, data.from_cache, origFn);
        }
      }).catch(function() {
        self.setError();
      });
    }
  });

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      var drawer = document.getElementById('ai-drawer');
      if (drawer && drawer.classList.contains('open')) window.aiDrawer.close();
    }
  });

})();
