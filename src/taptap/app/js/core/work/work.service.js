'use strict';

angular.
    module('core.work').
    factory('Works', [
        '$resource',
        function($resource) {
            return $resource('api/works/', {}, {
                query: {
                    method: 'GET',
                    isArray: true
                },
                add: {
                    method: 'POST'
                }
            }, {stripTrailingSlashes: false});
        }
    ]);

angular.
    module('core.work').
    factory('Work', [
        '$resource',
        function($resource) {
            return $resource('api/works/:workID', {}, {
                query: {
                    method: 'GET',
                    params: {workID: ''},
                    isArray: true
                }
            });
        }
    ]);