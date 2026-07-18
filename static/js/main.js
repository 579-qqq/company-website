/**
 * 杳氬崥浼佺瀹樼綉 - 涓昏剼鏈?
 */
document.addEventListener('DOMContentLoaded', function() {

    // ==========================================
    // 绉诲姩绔彍鍗曞垏鎹?
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
    // 骞虫粦婊氬姩鍒伴敋鐐?
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
    // 鏈嶅姟鍗＄墖灞曞紑/鏀惰捣
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
    // 椤甸潰鍔犺浇鏃舵鏌?hash 骞舵粴鍔ㄥ埌瀵瑰簲浣嶇疆
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
