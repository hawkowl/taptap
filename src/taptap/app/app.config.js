'use strict';

angular.
  module('taptapApp').
  config(['$locationProvider' ,'$routeProvider',
    function config($locationProvider, $routeProvider) {
      $locationProvider.hashPrefix('!');

      $routeProvider.
        when('/works', {
          template: '<work-list></work-list>'
        }).
        when('/works/new', {
          template: '<new-work></new-work>'
        }).
        when('/works/:workID', {
          template: '<work-detail></work-detail>'
        }).
        otherwise('/works');
    }
]);
