'use strict';

angular.
    module('workDetail').
    component('workDetail', {
        templateUrl: '/js/work-detail/work-detail.template.html',
        controller: [
            'Work', 'WordCount', '$scope', '$routeParams',
            function WorkDetailController(Work, WordCount, $scope, $routeParams) {
                $scope.work = Work.get({workID: $routeParams.workID})

                $scope.update = function() {
                    var input = {"count": $("#wc_number").val()};
                    WordCount.add({workID: $routeParams.workID}, input).$promise.then(
                        function(work) {
                            $scope.work = work;
                            $('#wordcount_modal').modal('hide');
                        })
                }

            }
        ]
    });
