'use strict';

angular.
    module('core.work').
    filter('words_to_time', function() {
        return function(word_count) {
            return "~" + Math.ceil(word_count / 275) + " min"
        }});
