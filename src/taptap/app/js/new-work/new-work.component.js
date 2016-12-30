'use strict';

angular.
  module('newWork').
    component('newWork', {
        templateUrl: '/js/new-work/new-work.template.html',
        controller: [
            'Works', "$scope", "$location",
            function NewWorkController(Works, $scope, $location) {
                $scope.update = function(work) {

                    Works.add(work).$promise.then(function (res) {

                        console.log(res)

                        $location.path("#!/works/" + res.id)

                    });
                }
            }
        ]
    });
