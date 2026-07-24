import * as THREE from './three/three.module.js';
import { OrbitControls } from './three/OrbitControls.js';
import { GLTFLoader } from './three/GLTFLoader.js';
import { RoomEnvironment } from './three/RoomEnvironment.js';


var controls,
    renderer,
    scene,
    camera,
    environment,
    loader;

var animationLoop = null;

$('.homepage-banner-item-360-toggle').on('click', function (e) {
  e.preventDefault();

  // $('#Model360Modal').modal('show');
  // return false;

  let item = $(this).data('preset');
  let source = $(this).data('src');

  // console.log(item);
  // console.log(source);

  scene = new THREE.Scene();
  scene.background = new THREE.Color('#F2F2F4');
  // scene.add(new THREE.AxesHelper());

  camera = new THREE.PerspectiveCamera( 75, window.innerWidth / window.innerHeight, 0.01, 10 );
  // camera.position.set(0, 0, 0.05);
  camera.position.set(0, 0, 0);

  // Kran
  if (item == 'kran') {
    camera.position.z = 0.06;
  }

  // Krug
  if (item == 'krug') {
    camera.position.z = 0.07;
  }


  var light1 = new THREE.AmbientLight(0xffffff, 0.3);
  // light1.name = 'ambient_light';


  var light2 = new THREE.DirectionalLight(0xffffff, 0.8 * Math.PI);
  light2.position.set(0.5, 0, 0.866); // ~60º
  // light2.name = 'main_light';

  camera.add(light1);
  camera.add(light2);

  scene.add(light1);
  scene.add(light2);


  renderer = new THREE.WebGLRenderer({
    antialias: true
  });

  renderer.shadowMap.enabled = true;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = Math.pow(2, -0.7125);
  // renderer.toneMappingExposure = 0.4;

  renderer.setSize( window.innerWidth, window.innerHeight );
  renderer.setPixelRatio( window.devicePixelRatio );
  renderer.setClearColor('#F2F2F4');

  $('.models-360-placeholder').html(renderer.domElement);
  // document.body.appendChild( renderer.domElement );


  controls = new OrbitControls( camera, renderer.domElement );
  controls.enableDamping = true;
  // controls.autoRotate = true;
  // controls.autoRotateSpeed = 1.25;

  // Kran
  if (item == 'kran') {
    controls.minDistance = 0.025;
    controls.maxDistance = 0.06;
  }

  // Krug
  if (item == 'krug') {
    controls.minDistance = 0.035;
    controls.maxDistance = 0.07;
  }



  var loader = new GLTFLoader();
  loader.load(
    source,
    // '/roke-fittings-study/local/templates/roke/assets/models/krug.glb',

    function ( gltf ) {

      // gltf.scene.updateMatrixWorld();
      // gltf.scene.updateMatrix();

      var mroot = gltf.scene;
      var bbox = new THREE.Box3().setFromObject(mroot);
      var cent = bbox.getCenter(new THREE.Vector3());
      var size = bbox.getSize(new THREE.Vector3());

      //Rescale the object to normalized space
      var maxAxis = Math.max(size.x, size.y, size.z);
      // mroot.scale.multiplyScalar(1.0 / maxAxis);
      bbox.setFromObject(mroot);
      bbox.getCenter(cent);
      bbox.getSize(size);
      //Reposition to 0,halfY,0
      mroot.position.copy(cent).multiplyScalar(-1);
      // mroot.position.y-= (size.y * 0.5);

      scene.add( gltf.scene );

    }, function ( xhr ) {

      let progress = parseInt(xhr.loaded / xhr.total * 100);
      // console.log( progress + '% loaded' );

      if (progress >= 100) {
        setTimeout(function () {
          $('.models-360-placeholder').removeClass('clear');
        }, 1000);
      }

    }, function ( error ) {

  	console.error( error );

  } );

  // console.log(loader);


  var environment = new RoomEnvironment( renderer );
  var pmremGenerator = new THREE.PMREMGenerator( renderer );
  scene.environment = pmremGenerator.fromScene( environment ).texture;
  pmremGenerator.compileEquirectangularShader();

  // environment.dispose();

  animate();


  $('#Model360Modal').modal('show');
});


function animate () {
  if (animationLoop) {
    cancelAnimationFrame(animationLoop);
  }
  animationLoop = requestAnimationFrame(animate);
  if (controls) {
    controls.update();
  }
  if (scene && camera) {
    renderer.render(scene, camera);
  }
  // stats.update()
}

function stopAnimationLoop () {
  cancelAnimationFrame(animationLoop);
}


$('#Model360Modal').on('hidden.bs.modal', function () {

  try {
      // Properly dispose of resources
      if (renderer) renderer.dispose(); // Dispose the renderer
      if (environment) environment.dispose();
      if (scene) scene.traverse(object => {
         if (object.isMesh) {
            object.geometry.dispose(); // Dispose geometry
            object.material.dispose(); // Dispose material
         }
      });
      // Nullify references
      // group = null;
      controls = null;
      camera = null;
      scene = null;
      environment = null;

      // scene.remove(scene.children[0]);

   } catch (err) {
      console.log('Modal close: ' + err.message);
   }

   try {
     $('.models-360-placeholder').empty();
     $('.models-360-placeholder').addClass('clear');
   } catch (err) {
      console.log('Modal close: ' + err.message);
   }

  // console.log('renderer.info.memory after: ', renderer.info);
});
