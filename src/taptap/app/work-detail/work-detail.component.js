'use strict';

angular.
    module('workDetail').
    component('workDetail', {
        templateUrl: 'work-detail/work-detail.template.html',
        controller: [
            'Work', '$routeParams',
            function WorkDetailController(Work, $routeParams) {
                var self = this;
                self.work = Work.get({workID: $routeParams.workID})
            }
        ]
    });
