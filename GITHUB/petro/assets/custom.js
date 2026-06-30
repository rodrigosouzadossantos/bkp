Reveal.on("slidechanged", function(event) {
  const svgs = event.currentSlide.querySelectorAll("svg");
  svgs.forEach(svg => {
    svg.querySelectorAll("animate").forEach(anim => {
      anim.beginElement();
    });
  });
});
