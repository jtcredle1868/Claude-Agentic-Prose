/* ============================================
   THE KEEPSAKE COMPANY - Main JavaScript
   ============================================ */

document.addEventListener('DOMContentLoaded', function () {

    // --- Mobile Navigation Toggle ---
    const mobileToggle = document.getElementById('mobileToggle');
    const mainNav = document.getElementById('mainNav');

    if (mobileToggle && mainNav) {
        mobileToggle.addEventListener('click', function () {
            this.classList.toggle('active');
            mainNav.classList.toggle('active');
        });

        // Mobile dropdown toggle
        const dropdownItems = mainNav.querySelectorAll('.has-dropdown');
        dropdownItems.forEach(function (item) {
            item.querySelector('a').addEventListener('click', function (e) {
                if (window.innerWidth <= 768) {
                    // Only prevent default if clicking the parent link on mobile
                    const dropdown = item.querySelector('.dropdown-menu');
                    if (dropdown) {
                        e.preventDefault();
                        item.classList.toggle('open');
                    }
                }
            });
        });
    }

    // --- Sticky Header Shadow on Scroll ---
    const header = document.getElementById('mainHeader');
    if (header) {
        window.addEventListener('scroll', function () {
            if (window.scrollY > 100) {
                header.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.4)';
            } else {
                header.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.3)';
            }
        });
    }

    // --- Hero Carousel ---
    const carousel = document.getElementById('heroCarousel');
    if (carousel) {
        const slides = carousel.querySelectorAll('.carousel-slide');
        const indicators = carousel.querySelectorAll('.indicator');
        const prevBtn = carousel.querySelector('.carousel-control.prev');
        const nextBtn = carousel.querySelector('.carousel-control.next');
        let currentSlide = 0;
        let autoPlayInterval;

        function goToSlide(index) {
            slides[currentSlide].classList.remove('active');
            indicators[currentSlide].classList.remove('active');
            currentSlide = (index + slides.length) % slides.length;
            slides[currentSlide].classList.add('active');
            indicators[currentSlide].classList.add('active');
        }

        function nextSlide() {
            goToSlide(currentSlide + 1);
        }

        function prevSlide() {
            goToSlide(currentSlide - 1);
        }

        function startAutoPlay() {
            autoPlayInterval = setInterval(nextSlide, 5000);
        }

        function stopAutoPlay() {
            clearInterval(autoPlayInterval);
        }

        // Controls
        if (nextBtn) nextBtn.addEventListener('click', function () { stopAutoPlay(); nextSlide(); startAutoPlay(); });
        if (prevBtn) prevBtn.addEventListener('click', function () { stopAutoPlay(); prevSlide(); startAutoPlay(); });

        // Indicators
        indicators.forEach(function (indicator, index) {
            indicator.addEventListener('click', function () {
                stopAutoPlay();
                goToSlide(index);
                startAutoPlay();
            });
        });

        // Pause on hover
        carousel.addEventListener('mouseenter', stopAutoPlay);
        carousel.addEventListener('mouseleave', startAutoPlay);

        // Touch support
        let touchStartX = 0;
        let touchEndX = 0;

        carousel.addEventListener('touchstart', function (e) {
            touchStartX = e.changedTouches[0].screenX;
            stopAutoPlay();
        }, { passive: true });

        carousel.addEventListener('touchend', function (e) {
            touchEndX = e.changedTouches[0].screenX;
            if (touchStartX - touchEndX > 50) {
                nextSlide();
            } else if (touchEndX - touchStartX > 50) {
                prevSlide();
            }
            startAutoPlay();
        }, { passive: true });

        // Start autoplay
        startAutoPlay();
    }

    // --- Gallery Filter ---
    const filterBtns = document.querySelectorAll('.filter-btn');
    const galleryGrid = document.getElementById('galleryGrid');
    const storeGrid = document.getElementById('storeGrid');

    if (filterBtns.length > 0) {
        filterBtns.forEach(function (btn) {
            btn.addEventListener('click', function () {
                // Update active button
                filterBtns.forEach(function (b) { b.classList.remove('active'); });
                this.classList.add('active');

                const filter = this.getAttribute('data-filter');
                const grid = galleryGrid || storeGrid;

                if (grid) {
                    const items = grid.querySelectorAll('[data-category]');
                    items.forEach(function (item) {
                        if (filter === 'all' || item.getAttribute('data-category') === filter) {
                            item.style.display = '';
                        } else {
                            item.style.display = 'none';
                        }
                    });
                }
            });
        });
    }

    // --- Gallery Lightbox ---
    const lightbox = document.getElementById('lightbox');
    const lightboxImage = document.getElementById('lightboxImage');
    const lightboxClose = document.getElementById('lightboxClose');

    if (lightbox && galleryGrid) {
        const galleryItems = galleryGrid.querySelectorAll('.gallery-item');

        galleryItems.forEach(function (item) {
            item.addEventListener('click', function () {
                const img = this.querySelector('img');
                if (img && lightboxImage) {
                    lightboxImage.src = img.src;
                    lightboxImage.alt = img.alt;
                    lightbox.classList.add('active');
                    document.body.style.overflow = 'hidden';
                }
            });
        });

        if (lightboxClose) {
            lightboxClose.addEventListener('click', function () {
                lightbox.classList.remove('active');
                document.body.style.overflow = '';
            });
        }

        lightbox.addEventListener('click', function (e) {
            if (e.target === lightbox) {
                lightbox.classList.remove('active');
                document.body.style.overflow = '';
            }
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && lightbox.classList.contains('active')) {
                lightbox.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    }

    // --- Contact Form Handling ---
    const contactForm = document.getElementById('contactForm');
    if (contactForm) {
        contactForm.addEventListener('submit', function (e) {
            e.preventDefault();
            // Placeholder: Replace with actual form submission logic
            alert('Thank you for your message. We will be in touch shortly.');
            contactForm.reset();
        });
    }

    // --- Smooth Scroll for Anchor Links ---
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;

            const target = document.querySelector(targetId);
            if (target) {
                e.preventDefault();
                const headerHeight = header ? header.offsetHeight : 80;
                const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - headerHeight;
                window.scrollTo({ top: targetPosition, behavior: 'smooth' });

                // Close mobile nav if open
                if (mainNav && mainNav.classList.contains('active')) {
                    mainNav.classList.remove('active');
                    if (mobileToggle) mobileToggle.classList.remove('active');
                }
            }
        });
    });

    // --- Scroll Animations (Intersection Observer) ---
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe elements for scroll animation
    const animateElements = document.querySelectorAll(
        '.service-card, .why-us-card, .testimonial-card, .team-card, .value-card, .product-card, .service-detail'
    );

    animateElements.forEach(function (el) {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
});
