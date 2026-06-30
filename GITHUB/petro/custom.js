console.log('custom')
Reveal.on( 'slidechanged', event => {
    console.log('Slide changed!');
    console.log('Previous slide:', event.previousSlide);
    console.log('Current slide:', event.currentSlide);

    // Example: Add a specific behavior for the title slide (horizontal index 0)
    if (event.indexh === 0) {
        // Your custom logic for the first slide
        console.log('Welcome to the title slide!');
    } else {
        // Logic for other slides
    }
});
