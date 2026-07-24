'use strict';

var videow = $('#VideoAspectRatio').width();
var videoh = $('#VideoAspectRatio').height();


if ($(window).width() >= 992) {
  $('.video-item').css({
    'aspect-ratio': videow + '/' + videoh,
  });
}


document.addEventListener("DOMContentLoaded", (event) => {
  gsap.registerPlugin(ScrollTrigger);
  gsap.registerPlugin(TextPlugin);

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const companyText = "<span>ROKE Fluid Equipment</span> 成立于 2008 年，专注于为关键生产过程供应不锈钢、钛等材料的管路配件、阀门和管接头。BHS RUS 是 ROKE Fluid Equipment 工厂及其全系列产品在俄罗斯的官方独家经销商。";
  const productText = "<span>产品</span> 我们生产并供应碳钢、316/316L 不锈钢、双相钢、超级双相钢、哈氏合金、蒙乃尔合金、因科镍合金、因科洛伊合金和钛材产品。";

  if (!reducedMotion) {
    $('.about-hero-text-1, .about-hero-text-2').empty();
    var tl = gsap.timeline({
      scrollTrigger: {
        trigger: '.about-hero-scroll',
        start: "center bottom",
        end: "bottom bottom",
        scrub: 1,
        // markers: true,
      }
    });

    tl.to('.about-hero-text-1', {
      text: {
        value: companyText,
      }
    }).to('.about-hero-text-2', {
      text: {
        value: productText,
      }
    });
  }


  // gsap.to('.about-description-overlay', {
  //   top: '100%',
  //   opacity: 0.75,
  //   scrollTrigger: {
  //     scrub: 1,
  //     trigger: '.about-description',
  //     start: 'top 60%',
  //     end: 'bottom 40%',
  //     // markers: true,
  //   }
  // });


  let frameCount = 240;
  // let urls = new Array(frameCount).fill().map((o, i) => `/roke-fittings-study/upload/images/frames2/${(i+1).toString().padStart(4, '0')}.webp`);
  // let urls = new Array(frameCount).fill().map((o, i) => `/roke-fittings-study/upload/images/frames2_avif/${(i+1).toString().padStart(4, '0')}.avif`);

  // let urls = new Array(frameCount).fill().map((o, i) => `/roke-fittings-study/upload/images/frames2_new/${(i+1).toString().padStart(4, '0')}.webp`);

  // let urls = new Array(frameCount).fill().map((o, i) => `/roke-fittings-study/upload/images/frames2_new_kraken_fullhd/${(i+1).toString().padStart(4, '0')}.png`);
  let urls = new Array(frameCount).fill().map((o, i) => `/roke-fittings-study/upload/images/frames2_avif_new/${(i+1).toString().padStart(4, '0')}.avif`);

  imageSequence({
    urls, // Array of image URLs
    canvas: "#image-sequence-about", // <canvas> object to draw images to
    clear: true, // only necessary if your images contain transparency
    // onUpdate: (index, image) => console.log("drew image index", index, ", image:", image),
    // fps: 720,
    scrollTrigger: {
      // snap: 1,
      trigger: '.about-hero-scroll',
      scrub: true, // important!
      // start: 0,   // start at the very top
      // end: 790,
      // start: 'top',
      start: 0,
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

});
