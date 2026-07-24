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
      // value: "Компания ROKE Fluid Equipment, основанная в 2008 году, профессионально поставляет трубную арматуру, клапаны и фитинги из разных материалов. Мы находимся в Наньтуне, в 2 часах езды от Шанхая.",
      // value: "<span>Компания ROKE Fluid Equipment</span> Основана в 2008 году. Специализируемся на поставках трубной арматуры, клапанов и фитингов из нержавеющей стали, титана и других материалов для критически важных производственных процессов.",
      value: "<span>Компания ROKE Fluid Equipment</span> основана в 2008 году. Специализируемся на поставках трубной арматуры, клапанов и фитингов из нержавеющей стали, титана и других материалов для критически важных производственных процессов. Компания БХС РУС является официальным эксклюзивным дистрибьютором завода ROKE Fluid Equipment и всей продукции ROKE в России.",
    }
  }).to('.about-hero-text-2', {
    text: {
      // value: "Наша продукция используется в химической, нефтяной, энергетической и других отраслях. Мы обеспечиваем полное удовлетворение клиентов, предлагая оборудование для высокоточного производства и контроля качества.",
      value: "<span>Продукция</span> Мы производим и поставляем продукцию из углеродистой стали, нержавеющей стали 316/316L, дуплекса, супердуплекса, хастеллоя, монеля, инконеля, инколоя и титана.",
    }
  });


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
