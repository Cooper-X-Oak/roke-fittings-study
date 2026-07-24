'use strict';

var svgHeight = $('.hero-title-svg-wrapper').height();
var heroElementsHeight = $('.hero-elements').height();
var heroFramesHeight = svgHeight / 4;

// console.log('svgHeight: ', svgHeight);
// console.log('heroFramesHeight: ', heroFramesHeight);
// console.log('heroElementsHeight: ', heroElementsHeight);


$('.hero-frames').height(heroFramesHeight);

document.addEventListener("DOMContentLoaded", (event) => {
  gsap.registerPlugin(ScrollTrigger);


  // gsap.fromTo('.section-promo', {
  //   backgroundPositionY: 'calc(var(--fs-16) * 6.25)',
  // }, {
  //   backgroundPositionY: 'calc(var(--fs-16) * 20)',
  //   scrollTrigger: {
  //     trigger: '.section-promo',
  //     scrub: true,
  //     start: 'top bottom',
  //     // markers: true,
  //   }
  // });

  gsap.to('.hero-title-svg-wrapper', {
    bottom: '110%',
    scrollTrigger: {
      trigger: '.hero-wrapper',
      scrub: true,
      start: 'top',
      end: 'bottom top',
      // markers: true,
    }
  });

  gsap.to('.hero-title-svg', {
    opacity: 0,
    scrollTrigger: {
      trigger: '.hero-wrapper',
      scrub: true,
      start: 'top',
      end: 'bottom top',
      // markers: true,
    }
  });


  gsap.to('.hero-info', {
    opacity: 1,
    y: 0,
    scrollTrigger: {
      trigger: '.hero-wrapper',
      scrub: true,
      start: 'bottom top',
      end: 'bottom',
      duration: 2,
    }
  });


  gsap.to('.hero-frames', {
    height: heroElementsHeight,
    scrollTrigger: {
      trigger: '.hero-wrapper',
      scrub: true,
      start: 'top',
      end: 'bottom',
    }
  });



  let frameCount = 240;
  // let urls = new Array(frameCount).fill().map((o, i) => `/roke-fittings-study/upload/images/frames1/${(i+1).toString().padStart(4, '0')}.webp`);
  // let urls = new Array(frameCount).fill().map((o, i) => `/roke-fittings-study/upload/images/frames1_avif/${(i+1).toString().padStart(4, '0')}.avif`);

  // let urls = new Array(frameCount).fill().map((o, i) => `/roke-fittings-study/upload/images/frames1_new/${(i+1).toString().padStart(4, '0')}.webp`);
  // let urls = new Array(frameCount).fill().map((o, i) => `/roke-fittings-study/upload/images/frames1_new_kraken/${(i+1).toString().padStart(4, '0')}.webp`);

  // let urls = new Array(frameCount).fill().map((o, i) => `/roke-fittings-study/upload/images/frames1_new_kraken_fullhd/${(i+1).toString().padStart(4, '0')}.png`);
  let urls = new Array(frameCount).fill().map((o, i) => `/roke-fittings-study/upload/images/frames1_avif_new/${(i+1).toString().padStart(4, '0')}.avif`);

  imageSequence({
    urls, // Array of image URLs
    canvas: "#image-sequence", // <canvas> object to draw images to
    clear: true, // only necessary if your images contain transparency
    // onUpdate: (index, image) => console.log("drew image index", index, ", image:", image),
    // fps: 720,
    scrollTrigger: {
      trigger: '.hero-wrapper',
      // snap: 1,
      scrub: true, // important!
      start: 0,   // start at the very top
      end: 'bottom',
      // end: "max", // entire page
      // markers: true,
    }
  });


  let frameCount3 = 170;
  // let urls3 = new Array(frameCount3).fill().map((o, i) => `/roke-fittings-study/upload/images/frames3/${(i+1).toString().padStart(4, '0')}.webp`);
  let urls3 = new Array(frameCount3).fill().map((o, i) => `/roke-fittings-study/upload/images/frames3_avif/${(i+1).toString().padStart(4, '0')}.avif`);
  // console.log(urls3);

  gsap.to('#section-promo-image-sequence', {
    scale: 1.025,
    scrollTrigger: {
      trigger: '.section-promo',
      scrub: true,
      start: 'top top',
      end: 'bottom bottom',
      // markers: true,
    }
  });

  imageSequence({
    urls: urls3, // Array of image URLs
    canvas: "#section-promo-image-sequence", // <canvas> object to draw images to
    clear: true, // only necessary if your images contain transparency
    // onUpdate: (index, image) => console.log("drew image index", index, ", image:", image),
    // fps: 720,
    scrollTrigger: {
      trigger: '.section-promo',
      // snap: 1,
      scrub: true, // important!
      start: 'top top',
      end: 'bottom bottom',
      // end: "max", // entire page
      // markers: true,
    }
  });


  /*
  Helper function that handles scrubbing through a sequence of images, drawing the appropriate one to the provided canvas.
  Config object properties:
  - urls [Array]: an Array of image URLs
  - canvas [Canvas]: the <canvas> object to draw to
  - scrollTrigger [Object]: an optional ScrollTrigger configuration object like {trigger: "#trigger", start: "top top", end: "+=1000", scrub: true, pin: true}
  - clear [Boolean]: if true, it'll clear out the canvas before drawing each frame (useful if your images contain transparency)
  - paused [Boolean]: true if you'd like the returned animation to be paused initially (this isn't necessary if you're passing in a ScrollTrigger that's scrubbed, but it is helpful if you just want a normal playback animation)
  - fps [Number]: optional frames per second - this determines the duration of the returned animation. This doesn't matter if you're using a scrubbed ScrollTrigger. Defaults to 30fps.
  - onUpdate [Function]: optional callback for when the Tween updates (probably not used very often). It'll pass two parameters: 1) the index of the image (zero-based), and 2) the Image that was drawn to the canvas

  Returns a Tween instance
  */
  function imageSequence(config) {
    let playhead = {frame: 0},
        canvas = gsap.utils.toArray(config.canvas)[0] || console.warn("canvas not defined"),
        ctx = canvas.getContext("2d"),
        curFrame = -1,
        onUpdate = config.onUpdate,
        images,
        updateImage = function() {
          let frame = Math.round(playhead.frame);
          if (frame !== curFrame) { // only draw if necessary
            config.clear && ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(images[Math.round(playhead.frame)], 0, 0);
            curFrame = frame;
            onUpdate && onUpdate.call(this, frame, images[frame]);
          }
        };
    images = config.urls.map((url, i) => {
      let img = new Image();
      // img.src = url;
      setTimeout(function () {
        img.src = url;
      }, 700)
      i || (img.onload = updateImage);
      return img;
    });
    return gsap.to(playhead, {
      frame: images.length - 1,
      ease: "none",
      onUpdate: updateImage,
      duration: images.length / (config.fps || 30),
      paused: !!config.paused,
      scrollTrigger: config.scrollTrigger
    });
  }

});
