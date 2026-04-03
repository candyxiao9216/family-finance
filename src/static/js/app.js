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

  // 在每个统计栏上方插入眼睛按钮
  var statsBars = document.querySelectorAll('.stats-bar');
  statsBars.forEach(function(bar) {
    var wrapper = document.createElement('div');
    wrapper.style.cssText = 'display:flex;justify-content:flex-end;margin-bottom:-8px;';
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
    wrapper.appendChild(eyeBtn);
    bar.parentNode.insertBefore(wrapper, bar);
  });

  function applyDataVisibility() {
    document.querySelectorAll('.stat-value').forEach(function(el) {
      if (isHidden) {
        if (!el.dataset.original) el.dataset.original = el.textContent;
        el.textContent = '****';
      } else {
        if (el.dataset.original) el.textContent = el.dataset.original;
      }
    });
  }

  if (isHidden) applyDataVisibility();

})();
