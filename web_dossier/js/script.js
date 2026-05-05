// =========================================
// MARQUESINAS DE GALICIA - FUNCIONALIDADES JS
// =========================================

// === MENÚ MÓVIL ===
document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const navMenu = document.getElementById('navMenu');
    
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
            this.classList.toggle('active');
        });
    }
    
    // Cerrar menú al hacer clic en un enlace
    const navLinks = document.querySelectorAll('.nav-menu a');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            navMenu.classList.remove('active');
            if (mobileMenuToggle) {
                mobileMenuToggle.classList.remove('active');
            }
        });
    });
});

// === SCROLL SUAVE ===
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const targetId = this.getAttribute('href');
        if (targetId === '#') return;
        
        const targetElement = document.querySelector(targetId);
        if (targetElement) {
            const headerOffset = 80;
            const elementPosition = targetElement.getBoundingClientRect().top;
            const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

            window.scrollTo({
                top: offsetPosition,
                behavior: 'smooth'
            });
        }
    });
});

// === HEADER SCROLL EFFECT ===
window.addEventListener('scroll', function() {
    const header = document.querySelector('.main-header');
    if (window.scrollY > 100) {
        header.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.2)';
    } else {
        header.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1)';
    }
});

// === LIGHTBOX DE GALERÍA ===
function openLightbox(imageSrc, caption) {
    const lightbox = document.getElementById('lightbox');
    const lightboxImg = document.getElementById('lightbox-img');
    const lightboxCaption = document.getElementById('lightbox-caption');
    
    if (lightbox && lightboxImg) {
        lightboxImg.src = imageSrc;
        lightboxCaption.textContent = caption || '';
        lightbox.classList.add('active');
        lightbox.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

function closeLightbox() {
    const lightbox = document.getElementById('lightbox');
    if (lightbox) {
        lightbox.classList.remove('active');
        lightbox.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

// Cerrar lightbox con tecla ESC
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeLightbox();
    }
});

// === ANIMACIONES AL SCROLL ===
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// Aplicar animaciones a elementos
document.addEventListener('DOMContentLoaded', function() {
    const animatedElements = document.querySelectorAll('.objective-card, .product-card, .timeline-item, .benefit-item, .gallery-item');
    
    animatedElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
});

// === CONTADOR DE SCROLL ===
window.addEventListener('scroll', function() {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const scrollHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    const scrollPercentage = (scrollTop / scrollHeight) * 100;
    
    // Aquí se podría añadir una barra de progreso si se desea
    // document.getElementById('progress-bar').style.width = scrollPercentage + '%';
});

// === MENSAJE DE BIENVENIDA EN CONSOLA ===
console.log('%c Marquesinas de Galicia - Dossier Profesional ', 'background: #1e3a8a; color: #fff; font-size: 16px; padding: 10px; border-radius: 5px;');
console.log('%c Proyecto de documentación y preservación del patrimonio arquitectónico de Galicia ', 'color: #3b82f6; font-size: 12px;');
console.log('%c Contacto: robertoalmela300@gmail.com | +34 644 312 776 ', 'color: #64748b; font-size: 10px;');

// === PRELOAD DE IMÁGENES ===
window.addEventListener('load', function() {
    // Aplicar fade-in al hero cuando todo cargue
    const heroContent = document.querySelector('.hero-content');
    if (heroContent) {
        heroContent.style.animation = 'fadeInUp 1s ease-out';
    }
});

// === DETECCIÓN DE DISPOSITIVO ===
const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
if (isMobile) {
    document.body.classList.add('mobile-device');
}

// === FUNCIONES DE UTILIDAD ===
// Validar email (por si se añade formulario de contacto)
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(String(email).toLowerCase());
}

// Copiar texto al portapapeles
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        console.log('Texto copiado: ' + text);
    }, function(err) {
        console.error('Error al copiar: ', err);
    });
}