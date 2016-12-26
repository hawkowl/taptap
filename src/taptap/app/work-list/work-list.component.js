'use strict';

angular.
    module('workList').
    component('workList', {
        templateUrl: 'work-list/work-list.template.html',
        controller: [
            'Works',
            function WorkListController(Works) {
                this.works = Works.query()
                this.orderProp = 'age';
            }
        ]
    });
