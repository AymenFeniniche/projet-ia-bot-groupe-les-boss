document.addEventListener("DOMContentLoaded", () => {
  
  const btnBurger = document.querySelector("#menu-burger");
  const nav = document.querySelector(".navigation");
  const header = document.querySelector("header");

  if (btnBurger && nav) {
    btnBurger.addEventListener("click", () => {
      nav.classList.toggle("active");
      btnBurger.classList.toggle("bx-x");
      if (header && window.scrollY === 0) header.classList.toggle("active");
    });

    document.querySelectorAll(".navigation a").forEach((a) => {
      a.addEventListener("click", () => {
        nav.classList.remove("active");
        btnBurger.classList.remove("bx-x");
      });
    });
  }

  
  if (header) {
    const onScroll = () => header.classList.toggle("active", window.scrollY > 0);
    onScroll();
    window.addEventListener("scroll", onScroll);
  }

  if (typeof Swiper !== "undefined" && document.querySelector(".home")) {
    new Swiper(".home", {
      spaceBetween: 50,
      centeredSlides: true,
      autoplay: { delay: 5000, disableOnInteraction: false },
      pagination: { el: ".swiper-pagination", clickable: true },
    });
  }
});
