'use strict';

var HERO_TITLE_REFERENCE_WIDTH = 817;
var HERO_TITLE_REFERENCE_HEIGHT = 204;
var heroMotionMediaQuery = window.matchMedia
  ? window.matchMedia('(prefers-reduced-motion: reduce)')
  : { matches: false };
var heroSequenceCanvasElement = document.querySelector('#image-sequence');
var isHeroStaticSample = heroSequenceCanvasElement && heroSequenceCanvasElement.dataset.staticSample === 'true';

function clampHeroHeight(value, min, max) {
  return Math.min(Math.max(value, min), Math.max(min, max));
}

function measureHeroLayout() {
  var heroElements = document.querySelector('.hero-elements');
  var heroTitle = document.querySelector('.hero-title');
  var heroElementsRect = heroElements ? heroElements.getBoundingClientRect() : { width: 0, height: 0 };
  var heroTitleInnerWidth = 0;

  if (heroTitle) {
    var heroTitleRect = heroTitle.getBoundingClientRect();
    var heroTitleStyle = window.getComputedStyle(heroTitle);
    heroTitleInnerWidth = Math.max(
      0,
      heroTitleRect.width
        - (parseFloat(heroTitleStyle.paddingLeft) || 0)
        - (parseFloat(heroTitleStyle.paddingRight) || 0)
    );
  }

  if (!heroTitleInnerWidth) {
    heroTitleInnerWidth = heroElementsRect.width;
  }

  var syntheticTitleHeight = heroTitleInnerWidth * HERO_TITLE_REFERENCE_HEIGHT / HERO_TITLE_REFERENCE_WIDTH;
  var heroElementsHeight = Math.round(heroElementsRect.height);
  var referenceStartHeight = syntheticTitleHeight / 4 || 56;
  var transparentAssetStartFloor = heroElementsHeight * 0.34;
  var startHeightMax = Math.max(56, heroElementsHeight * 0.35);
  var startHeight = Math.round(clampHeroHeight(Math.max(referenceStartHeight, transparentAssetStartFloor), 56, startHeightMax));

  return {
    heroElementsHeight: heroElementsHeight,
    heroTitleInnerWidth: Math.round(heroTitleInnerWidth),
    syntheticTitleHeight: Math.round(syntheticTitleHeight),
    startHeight: startHeight
  };
}

var initialHeroLayout = measureHeroLayout();
var initialHeroFramesHeight = heroMotionMediaQuery.matches && initialHeroLayout.heroElementsHeight
  ? initialHeroLayout.heroElementsHeight
  : initialHeroLayout.startHeight;

// console.log('heroFramesStartHeight: ', initialHeroLayout.startHeight);
// console.log('heroElementsHeight: ', initialHeroLayout.heroElementsHeight);


$('.hero-frames')
  .toggleClass('is-static-sample', !!isHeroStaticSample)
  .height(initialHeroFramesHeight);

document.addEventListener("DOMContentLoaded", (event) => {
  gsap.registerPlugin(ScrollTrigger);
  const reducedMotion = heroMotionMediaQuery.matches;

  const applyHeroFrameStart = () => {
    const layout = measureHeroLayout();
    gsap.set('.hero-frames', {
      height: reducedMotion && layout.heroElementsHeight ? layout.heroElementsHeight : layout.startHeight
    });
    return layout;
  };

  applyHeroFrameStart();


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

  if (!reducedMotion && document.querySelector('.hero-title-svg-wrapper')) {
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
  }

  if (!reducedMotion && document.querySelector('.hero-title-svg')) {
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
  }

  if (reducedMotion) {
    gsap.set('.hero-info', { opacity: 1, y: 0 });
  } else {
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


    gsap.fromTo('.hero-frames', {
      height: () => measureHeroLayout().startHeight
    }, {
      height: () => measureHeroLayout().heroElementsHeight,
      ease: 'none',
      scrollTrigger: {
        trigger: '.hero-wrapper',
        scrub: true,
        start: 'top',
        end: 'bottom',
        invalidateOnRefresh: true,
      }
    });
  }



  const goal31HeroSequence = Object.freeze({
    frameCount: 240,
    fps: 30,
    durationSeconds: 8,
    basePath: '/ztovalue/assets/upload/images/zt-hero-fixed-ball-valve/',
  });
  let frameCount = goal31HeroSequence.frameCount;
  // let urls = new Array(frameCount).fill().map((o, i) => `/ztovalue/assets/upload/images/frames1/${(i+1).toString().padStart(4, '0')}.webp`);
  // let urls = new Array(frameCount).fill().map((o, i) => `/ztovalue/assets/upload/images/frames1_avif/${(i+1).toString().padStart(4, '0')}.avif`);

  // let urls = new Array(frameCount).fill().map((o, i) => `/ztovalue/assets/upload/images/frames1_new/${(i+1).toString().padStart(4, '0')}.webp`);
  // let urls = new Array(frameCount).fill().map((o, i) => `/ztovalue/assets/upload/images/frames1_new_kraken/${(i+1).toString().padStart(4, '0')}.webp`);

  // let urls = new Array(frameCount).fill().map((o, i) => `/ztovalue/assets/upload/images/frames1_new_kraken_fullhd/${(i+1).toString().padStart(4, '0')}.png`);
  let urls = new Array(frameCount).fill().map((o, i) => `${goal31HeroSequence.basePath}${(i+1).toString().padStart(4, '0')}.avif`);

  const heroSequenceCanvas = document.querySelector('#image-sequence');
  const heroFramesElement = document.querySelector('.hero-frames');
  if (heroSequenceCanvas && heroSequenceCanvas.dataset.staticSample !== 'true') {
    imageSequence({
      urls, // Array of image URLs
      canvas: "#image-sequence", // <canvas> object to draw images to
      clear: true, // only necessary if your images contain transparency
      onUpdate: () => heroFramesElement && heroFramesElement.classList.add('is-sequence-ready'),
      fps: goal31HeroSequence.fps,
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
  }


  let frameCount3 = 170;
  // let urls3 = new Array(frameCount3).fill().map((o, i) => `/ztovalue/assets/upload/images/frames3/${(i+1).toString().padStart(4, '0')}.webp`);
  let urls3 = new Array(frameCount3).fill().map((o, i) => `/ztovalue/assets/upload/images/frames3_avif/${(i+1).toString().padStart(4, '0')}.avif`);
  // console.log(urls3);

  if (!reducedMotion) {
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
  }

  imageSequence({
    urls: urls3, // Array of image URLs
    canvas: "#section-promo-image-sequence", // <canvas> object to draw images to
    clear: true, // only necessary if your images contain transparency
    // onUpdate: (index, image) => console.log("drew image index", index, ", image:", image),
    // fps: 720,
    scrollTrigger: reducedMotion ? undefined : {
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
        targetFrame = 0,
        drawRequest = 0,
        onUpdate = config.onUpdate,
        images,
        loadedFrames,
        nearestLoadedFrame = function(frame) {
          if (loadedFrames[frame]) {
            return frame;
          }
          for (let offset = 1; offset < loadedFrames.length; offset++) {
            let previous = frame - offset;
            let next = frame + offset;
            if (previous >= 0 && loadedFrames[previous]) {
              return previous;
            }
            if (next < loadedFrames.length && loadedFrames[next]) {
              return next;
            }
          }
          return -1;
        },
        updateImage = function() {
          drawRequest = 0;
          targetFrame = Math.max(0, Math.min(images.length - 1, Math.round(playhead.frame)));
          let frame = nearestLoadedFrame(targetFrame);
          if (frame >= 0 && frame !== curFrame) { // only draw a fully loaded frame
            config.clear && ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(images[frame], 0, 0, canvas.width, canvas.height);
            curFrame = frame;
            onUpdate && onUpdate.call(this, frame, images[frame]);
          }
        },
        requestDraw = function() {
          if (!drawRequest) {
            drawRequest = requestAnimationFrame(updateImage);
          }
        };
    loadedFrames = new Array(config.urls.length).fill(false);
    images = config.urls.map((url, i) => {
      let img = new Image();
      img.decoding = "async";
      img.onload = function() {
        loadedFrames[i] = true;
        if (i === 0 || i === targetFrame || curFrame < 0) {
          requestDraw();
        }
      };
      setTimeout(function () {
        img.src = url;
      }, i === 0 ? 0 : 120);
      return img;
    });
    return gsap.to(playhead, {
      frame: images.length - 1,
      ease: "none",
      onUpdate: requestDraw,
      duration: images.length / (config.fps || 30),
      paused: reducedMotion || !!config.paused,
      scrollTrigger: reducedMotion ? undefined : config.scrollTrigger
    });
  }

  if (reducedMotion) {
    ScrollTrigger.getAll().forEach((trigger) => trigger.kill());
  }

});
