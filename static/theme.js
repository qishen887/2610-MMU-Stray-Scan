(function () {
    'use strict';

    try {
        if (localStorage.getItem('nightMode') === 'true') {
            document.documentElement.dataset.theme = 'night';
        } else {
            delete document.documentElement.dataset.theme;
        }
    } catch (error) {
        console.warn('Unable to load the saved theme.', error);
    }
})();
