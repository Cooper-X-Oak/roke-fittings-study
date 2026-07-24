'use strict';

// const images = document.images;
// const videos = document.video;
// const imagesLength = images.length;
// const videosLength = videos.length;

var files;
var modal_files;
var marquee_duration = 15000;

AOS.init();

Fancybox.bind('[data-fancybox]', {
  Hash: false,
});

(function ($) {

  let textareas = document.querySelectorAll('.txta'),
      hiddenDiv = document.createElement('div'),
      content = null;

  for (let j of textareas) {
    j.classList.add('txtstuff');
  }

  hiddenDiv.classList.add('txta');
  hiddenDiv.style.display = 'none';
  hiddenDiv.style.whiteSpace = 'pre-wrap';
  hiddenDiv.style.wordWrap = 'break-word';

  for (let i of textareas) {
    (function (i) {
      // Note: Use 'keyup' instead of 'input'
      // if you want older IE support
      i.addEventListener('input', function () {

        // Append hiddendiv to parent of textarea, so the size is correct
        i.parentNode.appendChild(hiddenDiv);

        // Remove this if you want the user to be able to resize it in modern browsers
        i.style.resize = 'none';

        // This removes scrollbars
        i.style.overflow = 'hidden';

        // Every input/change, grab the content
        content = i.value;

        // Add the same content to the hidden div

        // This is for old IE
        content = content.replace(/\n/g, '<br>');

        // The <br ..> part is for old IE
        // This also fixes the jumpy way the textarea grows if line-height isn't included
        hiddenDiv.innerHTML = content + '<br style="line-height: 3px;">';

        // Briefly make the hidden div block but invisible
        // This is in order to read the height
        hiddenDiv.style.visibility = 'hidden';
        hiddenDiv.style.display = 'block';
        i.style.height = hiddenDiv.offsetHeight + 'px';

        // Make the hidden div display:none again
        hiddenDiv.style.visibility = 'visible';
        hiddenDiv.style.display = 'none';
      });
    })(i);
  }

  $('.phone-mask').mask("+7 (999) 999-99-99");

  var paddingLeft = $('.container-fluid').css('padding-left');
  paddingLeft = parseFloat(paddingLeft);

  var fontSize = parseFloat($('html').css('font-size'));
  const swiperA11y = {
    enabled: true,
    prevSlideMessage: '上一项',
    nextSlideMessage: '下一项',
    firstSlideMessage: '第一项',
    lastSlideMessage: '最后一项',
    paginationBulletMessage: '转到第 {{index}} 项',
    slideLabelMessage: '第 {{index}} 项，共 {{slidesLength}} 项',
  };
  // console.log(paddingLeft);
  // console.log(fontSize);


  const swiperBestsellers = new Swiper('.swiper-bestsellers', {
    a11y: swiperA11y,
    // slidesPerView: "auto",
    slidesPerView: 4.5,
    slidesOffsetBefore: paddingLeft,
    slidesOffsetAfter: paddingLeft,

    navigation: {
      nextEl: '.bestsellers-swiper-button-next',
      prevEl: '.bestsellers-swiper-button-prev',
    },

    breakpoints: {
      0: {
        spaceBetween: 4,
        slidesPerView: 1.5,
      },
      576: {
        spaceBetween: 4,
        slidesPerView: 3.5,
      },
      768: {
        spaceBetween: 4,
        slidesPerView: 4.5,
      },
      992: {
        spaceBetween: fontSize / 4,
        slidesPerView: 4.5,
      }
    }

  });

  const swiperPartners = new Swiper('.swiper-partners', {
    a11y: swiperA11y,

    spaceBetween: 16,

    navigation: {
      nextEl: '.partners-swiper-button-next',
      prevEl: '.partners-swiper-button-prev',
    },

    breakpoints: {
      0: {
        slidesPerView: 2,
      },
      576: {
        slidesPerView: 3,
      },
      768: {
        slidesPerView: 4,
      },
      992: {
        slidesPerView: 5,
      }
    }

  });

  // const swiperHomepageBanner = new Swiper('.homepage-banner-swiper', {
  //   grabCursor: true,
  //   navigation: {
  //     nextEl: '.homepage-banner-item-button-next',
  //     prevEl: '.homepage-banner-item-button-prev',
  //   },
  // });

  const swiperBanners = new Swiper('.swiper-banners', {
    a11y: swiperA11y,
    grabCursor: true,

    // autoplay: {
    //   delay: 5000,
    //   disableOnInteraction: false,
    // },

    pagination: {
      el: '.section-banner-pagination',
      clickable: true,
    },

    // scrollbar: {
    //   el: '.section-banner-scrollbar',
    //   draggable: true,
    // },

    // navigation: {
    //   nextEl: '.homepage-banner-item-button-next',
    //   prevEl: '.homepage-banner-item-button-prev',
    // },
  });

  const swiperCatalogSections = new Swiper('.swiper-catalog-sections', {
    a11y: swiperA11y,


    // grabCursor: true,
    // navigation: {
    //   nextEl: '.homepage-banner-item-button-next',
    //   prevEl: '.homepage-banner-item-button-prev',
    // },

    breakpoints: {
      0: {
        slidesPerView: 3.5,
        spaceBetween: 4,
      },
      576: {
        slidesPerView: 5.5,
        spaceBetween: 8,
      },
      768: {
        slidesPerView: 5.5,
        spaceBetween: 8,
      },
      992: {
        slidesPerView: 8,
        spaceBetween: fontSize,
      }
    }

  });


  var header = $('.header');
  var scrollPrev = 0;
  var headerOffsetTop = header.offset().top;
  // var scrollOffset = 50;
  var scrollOffset = header.height();
  // console.log(scrollOffset);

  if (headerOffsetTop > scrollOffset) {
    header.addClass('scrolled');
  } else {
    header.removeClass('scrolled');
  }

  $ (function () {
    const staticMirrorMessage = '这是前端学习镜像，不会提交或收集数据。';
    const staticCatalogMessage = '静态学习镜像展示完整产品目录，未包含原站的动态分类和产品详情接口。';

    $('[data-bs-toggle="offcanvas"]').attr('aria-label', '打开菜单');
    $('.btn-close').attr('aria-label', '关闭');
    $('#Model360Modal').attr('aria-label', '360° 产品模型');
    $('.homepage-banner-item-360-toggle')
      .attr({ role: 'button', tabindex: '0', 'aria-label': '查看 360° 产品模型' });
    $('.video-item-controls-play')
      .attr({ role: 'button', tabindex: '0', 'aria-label': '播放视频' });
    $('.grid-toggle-item').each(function () {
      $(this).attr({
        role: 'button',
        tabindex: '0',
        'aria-label': `切换为每行 ${$(this).data('cols')} 列`,
      });
    });
    $('.catalog-section-item').each(function () {
      let title = $(this).find('.catalog-section-item-title').text().trim();
      $(this).attr({
        role: 'button',
        tabindex: '0',
        'aria-label': `查看${title}分类`,
      });
    });
    $('.catalog-box-item-toggle').each(function () {
      let title = $(this)
        .find('.catalog-box-item-title, .bestseller-item-title, .homepage-card-item-title')
        .first()
        .text()
        .trim();
      $(this).attr({
        role: 'button',
        tabindex: '0',
        'aria-label': title ? `查看${title}` : '查看产品',
      });
    });
    $('input[placeholder], textarea[placeholder]').each(function () {
      if (!$(this).attr('aria-label')) {
        $(this).attr('aria-label', $(this).attr('placeholder'));
      }
    });

    $(document).on(
      'keydown',
      '.homepage-banner-item-360-toggle, .video-item-controls-play, .grid-toggle-item, .catalog-section-item, .catalog-box-item-toggle',
      function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          $(this).trigger('click');
        }
      }
    );

    // $(".form-control-phone").mask("+7 (999) 999-99-99");

    // $('#marquee1').marquee({
    // 	// duration: 33500,
    // 	duration: 25000,
    // 	delayBeforeStart: 0,
    // 	direction: 'left',
    // 	// duplicated: true,
    //   // startVisible: true,
    //   // gap: 80,
    // });
    //
    // $('#marquee2').marquee({
    // 	// duration: 33500,
    // 	duration: 25000,
    // 	delayBeforeStart: 0,
    // 	direction: 'left',
    // 	// duplicated: true,
    //   // startVisible: true,
    //   // gap: 80,
    // });
    //
    // $('#marquee3').marquee({
    // 	duration: 33500,
    // 	// duration: 25000,
    // 	delayBeforeStart: 0,
    // 	direction: 'left',
    // 	duplicated: true,
    //   startVisible: true,
    //   gap: 0,
    // });
    //
    // $('#marquee4').marquee({
    // 	// duration: 33500,
    // 	duration: 25000,
    // 	delayBeforeStart: 0,
    // 	direction: 'left',
    // 	// duplicated: true,
    //   // startVisible: true,
    //   // gap: 80,
    // });


    if ($(window).width() >= 992) {
      marquee_duration = 30000;
    }

    $('#marquee5').marquee({
    	// duration: 33500,
    	duration: marquee_duration,
    	delayBeforeStart: 0,
    	direction: 'left',
    	duplicated: true,
      startVisible: true,
      gap: 0,
    });


    $(document).on('scroll', function () {
      let $item = $('.section-benefits-image-scanner-wrapper');
      if ($item.length > 0) {
        let t = $item.offset().top - $item.offsetParent().offset().top;
        $('.section-benefits-image-scanner').css({
          'top': -t,
        });
      }
    });

    $(window).on('scroll', function() {
      let scrolled = $(window).scrollTop();

      if (scrolled > scrollOffset) {
        header.addClass('scrolled');
      } else {
        header.removeClass('scrolled');
        header.removeClass('in');
      }

      // if (scrolled > 300 && scrolled > scrollPrev) {
      if (scrolled > (fontSize * 20) && scrolled > scrollPrev) {
        if (scrolled - scrollPrev > 15) {
          header.addClass('out');
          $('body').addClass('header-out');
        }
      } else {
        if (scrolled - scrollPrev < -6) {
          header.removeClass('out');
          $('body').removeClass('header-out');
        }
      }
      scrollPrev = scrolled;
    });


    $('.video-item-controls-play').on('click', function (e) {
      e.preventDefault();
      // console.log(123);
      let videoItem = $(this).parents('.video-item');
      videoItem.addClass('playing');

      let v = videoItem.find('.video-item-object');

      $('.video-item-object').each(function () {
        if (!$(this).get(0).paused) {
          $(this).get(0).pause();
        }
      });

      if (v.get(0).paused) {
        // console.log(v.get(0));
        // if (!$(v.get(0)).parents('.video-item').hasClass('homepage-banner-video-item')) {
        //   v.attr('controls', true);
        // }
        v.attr('controls', true);
        // console.log(v.get(0));
        v.get(0).play();
      }
    });

    $('.video-item-object').on('pause', function (e) {
      let v = $(this);
      if (v.get(0).paused && !v.get(0).seeking) {
        v.removeAttr('controls');
        v.parents('.video-item').removeClass('playing');
      }
    });

    // $('.homepage-banner-video-item-object').on('click', function () {
    //   // console.log(123);
    //   // let v = $(this);
    //   $(this).get(0).pause();
    // });


    $('.grid-toggle-item').on('click', function () {
      let activeCols = $('.grid-toggle-item.active').data('cols');
      let cols = $(this).data('cols');
      $('.grid-toggle-item').removeClass('active');

      $('.catalog-box-row').removeClass('row-cols-md-' + activeCols);
      $('.catalog-box-row').addClass('row-cols-md-' + cols);
      $(this).addClass('active');
    });

    $('.catalog-section-item').on('click', function () {

      let index = parseInt($(this).data('index'));
      let $this = $(this);

      $('.catalog-section-item').removeClass('active');
      $this.addClass('active');
      document.querySelector('.catalog-tabs')?.scrollIntoView({
        behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
        block: 'start',
      });
      alert(staticCatalogMessage);
      return false;

      let data = {
        i: index
      };

      $.ajax({
        url: '/roke-fittings-study/ajax/catalog.tabs.php',
        type: 'POST',
        data,
        beforeSend: function (jqXHR, settings) {
          $('.catalog-section-item').removeClass('active');
        },
        success: function (res) {
          // console.log(res);

          $this.addClass('active');

          if ($('.catalog-section-item.active')) {
            $('.catalog-tabs').slideUp(400, function () {
              setTimeout(function () {
                $('.catalog-tabs').html(res);
                $('.catalog-tabs').slideDown(400);
              }, 200)
            });
          } else {
            $('.catalog-tabs').html(res);
            $('.catalog-tabs').slideDown(800);
          }
        },
        error: function (r) {
          // console.log(res);
          alert('请求失败');
        },
      })

    });

    $('.download-certs-tab-item').on('click', function () {
      $('.download-certs-tab-item').removeClass('active');
      $(this).addClass('active');

      let uid = $(this).data('uid');

      if (uid == 'all') {
        $('.download-cert-item-col').removeClass('inactive');
        return false;
      }

      $('.download-cert-item-col').removeClass('inactive');
      $('.download-cert-item-col[data-uid="' + uid + '"]').addClass('inactive');

    });


    $('.catalog-box-item-toggle').on('click', function () {
      let index = $(this).data('index');
      // console.log(i);

      alert(staticCatalogMessage);
      return false;

      let data = {
        i: index
      };

      $.ajax({
        url: '/roke-fittings-study/ajax/catalog.element.modal.php',
        type: 'POST',
        data,
        beforeSend: function (jqXHR, settings) {
          // $('.catalog-section-item').removeClass('active');
        },
        success: function (res) {
          // console.log(res);

          $('.catalog-box-item-placeholder').html(res);
          $('#ProductModal').modal('show');

        },
        error: function (r) {
          console.log(res);
          // alert('请求失败');
        },
      })

    });


    $('#RequestModalFile').on('change', function (e) {

      e.preventDefault();
      modal_files = this.files;

      if (modal_files.length == 0) return false;
      this.value = '';
      alert(staticMirrorMessage);
      return false;

      $.each(modal_files, function (key, value) {

        var formData = new FormData();
        formData.append(0, value);

        $.ajax({
          url: '/roke-fittings-study/ajax/upload-file.php',
          type: 'POST',
          data: formData,
          dataType: 'json',
          cache: false,
          processData: false,
          contentType: false,
          // xhr: function () {
          //   var xhr = new window.XMLHttpRequest();
          //   xhr.upload.addEventListener('progress', function (evt) {
          //     if (evt.lengthComputable) {
          //       var percentComplete = ((evt.loaded / evt.total) * 100);
          //       petUploadingContent.find('.pets-uploads-item-progress-line').width(percentComplete);
          //     }
          //   }, false);
          //   return xhr;
          // },
          // beforeSend: function (jqXHR, settings) {
          //
          // },
          success: function (res, status, jqXHR) {
            // console.log(res);
            var span = '<span class="userfile-title px-0 d-flex align-items-center"><span>' + res.filename + '</span><button type="button" class="btn d-flex align-items-center justify-content-center" data-key="' + res.filekey + '"><span aria-hidden="true" class="lh-1 text-danger">&times;</span></button></span>';
            var hidden = '<input type="hidden" class="userfile-name" name="files[]" id="' + res.filekey + '" value="' + res.savename + '" />';

            $('.userfiles-wrapper-modal').append($(span));
            $('.userfiles-wrapper-modal').append($(hidden));

          },
          error: function (res) {
            // console.log(res);
            alert('请求失败');
          }
        });

      });

    });

    $('#RequestModalForm').on('submit', function (e) {
      e.preventDefault();

      let form = $(this);
      let btn = form.find('.btn[type=submit]');
      let isValidated = true;

      form.find('.form-field-wrapper').removeClass('has-error');

      form.find('[form-required]').each(function () {
        let item = $(this);
        if (!item.val()) {
          item.parents('.form-field-wrapper').addClass('has-error');
          isValidated = false;
        }
      });

      if (!isValidated) return false;
      alert(staticMirrorMessage);
      return false;

      let userfiles = [];

      form.find('.userfile-name').each(function () {
        userfiles.push($(this).val());
      });

      let data = {
        author: form.find('#RequestModalAuthor').val(),
        phone: form.find('#RequestModalPhone').val(),
        email: form.find('#RequestModalEmail').val(),
        company: form.find('#RequestModalCompany').val(),
        // sku: form.find('#RequestModalSKU').val(),
        comment: form.find('#RequestModalComment').val(),
        userfiles: userfiles,
      };

      $.ajax({
        url: '/roke-fittings-study/ajax/request.modal.php',
        type: 'POST',
        data: data,
        beforeSend: function (jqXHR, settings) {
          btn.attr('disabled', true);
        },
        success: function (res) {
          // console.log(res);

          btn.attr('disabled', false);
          if (res.status == 1) {
            $('#RequestModal').modal('hide');
            $('#SuccessModal').modal('show');
          }

        },
        error: function (res) {
          // console.log(res);
          btn.attr('disabled', false);
          alert('请求失败');
        },
      });

    });


    // $('#FeedbackFormFileTrigger').on('click', function () {
    //   $('#FeedbackFormFile').trigger('click');
    // });

    $('#FeedbackForm').on('submit', function (e) {
      e.preventDefault();

      let form = $(this);
      let btn = form.find('.btn[type=submit]');
      let isValidated = true;

      form.find('.form-field-wrapper').removeClass('has-error');

      form.find('[form-required]').each(function () {
        let item = $(this);
        if (!item.val()) {
          item.parents('.form-field-wrapper').addClass('has-error');
          isValidated = false;
        }
      });

      let userfiles = [];

      form.find('.userfile-name').each(function () {
        userfiles.push($(this).val());
      });

      // console.log(userfiles);

      if (!isValidated) return false;
      alert(staticMirrorMessage);
      return false;

      let data = {
        author: form.find('#FeedbackFormAuthor').val(),
        phone: form.find('#FeedbackFormPhone').val(),
        email: form.find('#FeedbackFormEmail').val(),
        company: form.find('#FeedbackFormCompany').val(),
        comment: form.find('#FeedbackFormComment').val(),
        userfiles: userfiles,
      };

      $.ajax({
        url: '/roke-fittings-study/ajax/feedback.php',
        type: 'POST',
        data: data,
        beforeSend: function (jqXHR, settings) {
          btn.attr('disabled', true);
        },
        success: function (res) {
          console.log(res);

          btn.attr('disabled', false);
          if (res.status == 1) {
            $('#SuccessModal').modal('show');
          }

        },
        error: function (res) {
          // console.log(res);
          btn.attr('disabled', false);
          alert('请求失败');
        },
      });

    });


    $('#FeedbackFormFile').on('change', function (e) {

      e.preventDefault();
      files = this.files;

      if (files.length == 0) return false;
      this.value = '';
      alert(staticMirrorMessage);
      return false;

      $.each(files, function (key, value) {

        var formData = new FormData();
        formData.append(0, value);

        $.ajax({
          url: '/roke-fittings-study/ajax/upload-file.php',
          type: 'POST',
          data: formData,
          dataType: 'json',
          cache: false,
          processData: false,
          contentType: false,
          // xhr: function () {
          //   var xhr = new window.XMLHttpRequest();
          //   xhr.upload.addEventListener('progress', function (evt) {
          //     if (evt.lengthComputable) {
          //       var percentComplete = ((evt.loaded / evt.total) * 100);
          //       petUploadingContent.find('.pets-uploads-item-progress-line').width(percentComplete);
          //     }
          //   }, false);
          //   return xhr;
          // },
          // beforeSend: function (jqXHR, settings) {
          //
          // },
          success: function (res, status, jqXHR) {
            // console.log(res);
            var span = '<span class="userfile-title d-flex align-items-center"><span>' + res.filename + '</span><button type="button" class="btn d-flex align-items-center justify-content-center" data-key="' + res.filekey + '"><span aria-hidden="true" class="lh-1 text-danger">&times;</span></button></span>';
            var hidden = '<input type="hidden" class="userfile-name" name="files[]" id="' + res.filekey + '" value="' + res.savename + '" />';

            $('.userfiles-wrapper').append($(span));
            $('.userfiles-wrapper').append($(hidden));

          },
          error: function (res) {
            // console.log(res);
            alert('请求失败');
          }
        });

      });

    });

    $(document).on('click', '.userfile-title .btn', function (e) {
      e.preventDefault();
      let key = $(this).data('key');
      $(this).parents('.userfile-title').remove();
      $('#' + key).remove();
    });


  })
}) (jQuery)
