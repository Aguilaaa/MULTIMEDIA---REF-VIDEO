(function () {
  var toggle = document.querySelector(".nav-toggle");
  var mobile = document.getElementById("mobile-nav");

  if (toggle && mobile) {
    function setOpen(open) {
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      mobile.hidden = !open;
      document.body.style.overflow = open ? "hidden" : "";
    }

    toggle.addEventListener("click", function () {
      setOpen(mobile.hidden);
    });

    mobile.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        setOpen(false);
      });
    });

    window.addEventListener("resize", function () {
      if (window.innerWidth > 720) setOpen(false);
    });
  }
})();
