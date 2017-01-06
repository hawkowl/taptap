'use strict';

angular.
    module('workList').
    component('workList', {
        templateUrl: '/js/work-list/work-list.template.html',
        controller: [
            'Works',
            function WorkListController(Works) {
                this.works = Works.query()
                this.orderProp = 'name';

                this.is_done = function(work) {
                    if (work.completed == true) {
                        return "Completed"
                    } else {
                        return "In Progress"
                    }
                }

                this.showsparklines = function(work) {
                    $("#sparkline-" + work.id).sparkline(
                        'html',
                        {type: 'line', barColor: 'purple', width: "140px", height: "60px",
                         normalRangeMin: 0, normalRangeMax: work.word_target, disableInteraction: true})
                }

                this.sparkline = function(work) {
                    var done = []

                    for (var i = 0; i < work.counts.length; i++) {
                        done.push((work.counts[i].at - work.counts[0].at + 1) + ":" + work.counts[i].count)
                    }

                    if (work.completed == false) {
                        var d = new Date()
                        done.push((Math.ceil(d.getTime()/1000) - work.counts[0].at) + ":" + work.word_count)
                    }

                    return done.join(",")
                }
            }
        ]
    });
