/**
 * 垚博企管官网 - 主脚本
 */
document.addEventListener('DOMContentLoaded', function() {

    // ==========================================
    // 移动端菜单切换
    // ==========================================
    var mobileToggle = document.querySelector('.mobile-menu-toggle');
    if (mobileToggle) {
        mobileToggle.addEventListener('click', function() {
            var navMenu = document.querySelector('.nav-menu');
            if (navMenu) {
                navMenu.classList.toggle('nav-open');
            }
            this.classList.toggle('active');
        });
    }

    // ==========================================
    // 平滑滚动到锚点
    // ==========================================
    document.querySelectorAll('a[href*="#"]').forEach(function(link) {
        link.addEventListener('click', function(e) {
            var href = this.getAttribute('href');
            var hashIndex = href.indexOf('#');
            if (hashIndex === -1) return;

            var targetId = href.substring(hashIndex + 1);
            var pathPart = href.substring(0, hashIndex);

            var currentPath = window.location.pathname;
            if (pathPart && pathPart !== currentPath && pathPart !== '') {
                return;
            }

            var target = document.getElementById(targetId);
            if (target) {
                e.preventDefault();
                var offset = 80;
                var targetPosition = target.getBoundingClientRect().top + window.pageYOffset - offset;
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });

                if (history.pushState) {
                    history.pushState(null, null, '#' + targetId);
                }
            }
        });
    });

    // ==========================================
    // 服务卡片展开/收起
    // ==========================================
    document.querySelectorAll('.service-card-toggle').forEach(function(card) {
        card.addEventListener('click', function() {
            var detail = this.nextElementSibling;
            if (detail && detail.classList.contains('service-card-detail')) {
                var isOpen = detail.style.maxHeight && detail.style.maxHeight !== '0px';
                if (isOpen) {
                    detail.style.maxHeight = '0px';
                    detail.style.opacity = '0';
                    detail.style.padding = '0 24px';
                    this.classList.remove('expanded');
                } else {
                    detail.style.maxHeight = detail.scrollHeight + 'px';
                    detail.style.opacity = '1';
                    detail.style.padding = '20px 24px';
                    this.classList.add('expanded');
                }
            }
        });
    });

    // ==========================================
    // 页面加载时检查 hash 并滚动到对应位置
    // ==========================================
    if (window.location.hash) {
        var targetId = window.location.hash.substring(1);
        setTimeout(function() {
            var target = document.getElementById(targetId);
            if (target) {
                var offset = 80;
                var targetPosition = target.getBoundingClientRect().top + window.pageYOffset - offset;
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        }, 300);
    }

});
