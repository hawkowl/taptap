'use strict';

angular.
    module('workList').
    component('workList', {
        templateUrl: 'work-list/work-list.template.html',
        controller: [
            'Works',
            function WorkListController(Works) {
                this.works = Works.query()
                this.orderProp = 'name';

                this.showsparklines = function() {
                    $(".sparklines").sparkline('html', {type: 'line', barColor: 'purple',  width: "100%"})
                }

                this.sparkline = function(work) {

                    var done = []

                    for (var i = 0; i < work.counts.length; i++) {

                        done.push((work.counts[i].at - work.counts[0].at + 1) + ":" + work.counts[i].count)

                    }
                    var d = new Date()
                    done.push((Math.ceil(d.getTime()/1000) - work.counts[0].at) + ":" + work.word_count)

                    return done.join(",")

                }
            }
        ]
    });
