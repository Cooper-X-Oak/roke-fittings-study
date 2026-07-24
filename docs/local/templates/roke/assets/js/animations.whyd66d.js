'use strict';


document.addEventListener("DOMContentLoaded", (event) => {
  gsap.registerPlugin(ScrollTrigger);


  var tl = gsap.timeline({
    scrollTrigger: {
      // trigger: '.why-table-scroll',
      trigger: '.why-animations',
      start: "top center",
      // end: "bottom bottom",
      // scrub: 0,
      // markers: true,
      once: true,
    }
  });

  tl.to('#WhyTableItemCol-0', {
    opacity: 1,
    top: 0,
    // duration: 0.5
  }).to('#WhyTableItemCol-1', {
    opacity: 1,
    top: 0,
    // duration: 0.5
  }).to('#WhyTableItemCol-2', {
    opacity: 1,
    top: 0,
    // duration: 0.5
  }).to('#WhyTableItemCol-3', {
    opacity: 1,
    top: 0,
    // duration: 0.5
  }).to('#WhyTableItemCol-4', {
    opacity: 1,
    top: 0,
    // duration: 0.5
  });

});
