document.documentElement.classList.add('js');
(function(){
  var hd=document.getElementById('hd');
  var burger=document.getElementById('burger');
  var nav=document.getElementById('nav');

  // mobile menu
  burger.addEventListener('click',function(){document.body.classList.toggle('menu-open')});
  nav.addEventListener('click',function(e){if(e.target.tagName==='A')document.body.classList.remove('menu-open')});

  // header: solid on scroll, dark over dark sections, hide on scroll down
  var darks=[].slice.call(document.querySelectorAll('.dark,.ft'));
  var lastY=0;
  function onScroll(){
    var y=window.scrollY;
    hd.classList.toggle('is-solid',y>40);
    var overDark=darks.some(function(s){var r=s.getBoundingClientRect();return r.top<=36&&r.bottom>=36});
    hd.classList.toggle('is-dark',overDark);
    lastY=y;
  }
  window.addEventListener('scroll',onScroll,{passive:true});onScroll();

  // reveal (rect-based: robust inside iframes)
  var rvs=[].slice.call(document.querySelectorAll('.rv'));
  function reveal(){
    var h=window.innerHeight;
    rvs=rvs.filter(function(el){var r=el.getBoundingClientRect();if(r.top<h*0.94&&r.bottom>0){el.classList.add('is-in');return false}return true});
  }
  window.addEventListener('scroll',reveal,{passive:true});
  window.addEventListener('resize',reveal);
  reveal();
  setTimeout(reveal,300);

  // active nav
  var links=[].slice.call(nav.querySelectorAll('a[href^="#"]'));
  var secs=['about','approach','service','works','contact'].map(function(id){return document.getElementById(id)}).filter(Boolean);
  function activeNav(){
    var mid=window.innerHeight*0.5,cur=null;
    secs.forEach(function(s){var r=s.getBoundingClientRect();if(r.top<=mid&&r.bottom>mid)cur=s.id});
    links.forEach(function(l){l.classList.toggle('is-on',cur&&l.getAttribute('href')==='#'+cur)});
  }
  window.addEventListener('scroll',activeNav,{passive:true});activeNav();
})();
