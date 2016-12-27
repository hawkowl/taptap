'use strict';

angular.
  module('newWork').
    component('newWork', {
        templateUrl: '/js/new-work/new-work.template.html',
        controller: [
            'Works', "$scope", "$location",
            function NewWorkController(Works, $scope, $location) {
                $scope.update = function(work) {
                    $location.path("#!/works/" + 1)
                }
            }
        ]
    });
