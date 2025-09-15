// SFN - Secure Fast Network Scripts

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

    console.log('SFN website interactive features loaded.');
});
