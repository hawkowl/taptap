'use strict';

angular.
  module('newWork').
    component('newWork', {
        templateUrl: 'new-work/new-work.template.html',
        controller: [
            'Works', "$scope", "$location",
            function NewWorkController(Works, $scope, $location) {
                $scope.update = function(work) {
                    $location.path("#!/works/" + 1)
                }
            }
        ]
    });
