const btnBurger = document.querySelector('#menu-burger');
const nav = document.querySelector('.navigation');
const linkNav = document.querySelectorAll('.navigation a');
const header   = document.querySelector('header');
const sections = document.querySelectorAll('section');

if (btnBurger) {
    btnBurger.addEventListener('click', () => {
        nav.classList.toggle('active');
        btnBurger.classList.toggle('bx-x');
        if (window.scrollY === 0) {
            header.classList.toggle('active');
        }
    });
}

linkNav.forEach(link => {
    link.addEventListener('click', () => {
        if (nav) nav.classList.remove('active');
        if (btnBurger) btnBurger.classList.remove('bx-x');
    });
});

window.addEventListener('scroll', ()=> {
  header.classList.toggle('active', window.scrollY > 0)
});

//const scrollActive = () => {
    //sections.forEach(section => {
        //let top = window.scrollY;
        //let offset = section.offsetTop - 500;
        //let height = section.offsetHeight;
        //let id = section.getAttribute('id');
  
        //if (top >= offset && top < offset + height) {
        //    linkNav.forEach(link => link.classList.remove('link-active'));
        //    const activeLink = document.querySelector(`.navigation a[href*="${id}"]`);
        //    if (activeLink) activeLink.classList.add('link-active');
       // }
    //})
 // }
  
 // window.addEventListener('scroll', scrollActive)


var swiper = new Swiper('.home', {
    spaceBetween: 50,
    centeredSlides: true,
    autoplay: {
        delay: 5000,
        disableOnInteraction: false,
    },
    pagination: {
        el: '.swiper-pagination',
        clickable: true,
    },
});

