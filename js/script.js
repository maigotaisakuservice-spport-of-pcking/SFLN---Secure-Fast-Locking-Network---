// SFLN - Secure Fast Locking Network Scripts

document.addEventListener('DOMContentLoaded', () => {

    // --- Scroll Animation Observer ---
    const fadeInElements = document.querySelectorAll('.fade-in-element');

    const fadeInObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target); // Animate only once
            }
        });
    }, {
        threshold: 0.1 // Trigger when 10% of the element is visible
    });

    fadeInElements.forEach(el => {
        fadeInObserver.observe(el);
    });


    // --- Active Navigation Link Observer ---
    const sections = document.querySelectorAll('main section[id]');
    const navLinks = document.querySelectorAll('nav a');
    const navLinksMap = new Map();
    navLinks.forEach(link => {
        const hash = link.getAttribute('href');
        navLinksMap.set(hash.substring(1), link);
    });

    const navObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const id = entry.target.getAttribute('id');
                navLinks.forEach(link => link.classList.remove('active'));
                const activeLink = navLinksMap.get(id);
                if (activeLink) {
                    activeLink.classList.add('active');
                }
            }
        });
    }, {
        rootMargin: '-50% 0px -50% 0px', // Trigger when section is in the middle of the viewport
        threshold: 0
    });

    sections.forEach(section => {
        navObserver.observe(section);
    });


    // --- Download Button Logic ---
    const setupDownloadButtons = () => {
        const isDevelopment = true; // User requested: `true` for disabled, `false` for enabled

        const buttons = [
            { id: 'download-windows', platform: 'Windows', file: 'SFLN-Client-Windows.zip' },
            { id: 'download-android', platform: 'Android', file: 'SFLN-Client-Android.apk' },
            { id: 'download-linux', platform: 'Linux', file: 'SFLN-Client-Linux.tar.gz' }
        ];

        buttons.forEach(buttonInfo => {
            const buttonElement = document.getElementById(buttonInfo.id);
            if (!buttonElement) return;

            if (isDevelopment) {
                buttonElement.classList.add('disabled');
                buttonElement.textContent = `${buttonInfo.platform} (準備中)`;
                buttonElement.removeAttribute('href');
                buttonElement.onclick = (e) => e.preventDefault();
            } else {
                buttonElement.classList.remove('disabled');
                buttonElement.textContent = `${buttonInfo.platform} ダウンロード`;
                buttonElement.setAttribute('href', `downloads/${buttonInfo.file}`);
                buttonElement.onclick = () => alert(`「${buttonInfo.file}」のダウンロードを開始します...`);
            }
        });
    };

    setupDownloadButtons();

    console.log('SFLN website interactive features loaded.');
});
