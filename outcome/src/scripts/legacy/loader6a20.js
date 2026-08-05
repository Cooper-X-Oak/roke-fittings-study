'use strict';

// const resources = $('img, video, canvas');

// const resources = $('canvas');
// const totalResources = resources.length;
// var loadedResources = 0;
//
// function updateProgress() {
//   loadedResources++;
//   var percent = (loadedResources / totalResources) * 100;
//   percent = Math.round(percent);
//   // console.log(percent);
//   $('.loader-status').width(percent + '%');
// }
//
// resources.on('load', updateProgress).on('error', updateProgress);
//
// $(window).on('load',function() {
//   $('.loader-status').width(100 + '%');
//   $('.loader').delay(100).fadeOut(function () {
//     $('.loader').remove();
//   });
// });



if ($(window).width() >= 992) {
  if ('scrollRestoration' in history) {
    history.scrollRestoration = 'manual';
  }
  window.scrollTo(0, 0);
}
