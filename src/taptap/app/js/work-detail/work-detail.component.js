'use strict';

angular.
    module('workDetail').
    component('workDetail', {
        templateUrl: '/js/work-detail/work-detail.template.html',
        controller: [
            'Work', 'WordCount', 'DailyCounts', '$scope', '$routeParams',
            function WorkDetailController(Work, WordCount, DailyCounts, $scope, $routeParams) {
                var $this = this
                $scope.work = Work.get({workID: $routeParams.workID})


                $this.regraph = function() {
                    DailyCounts.query({workID: $routeParams.workID}).$promise.then(function(result) {

                        $scope.dailies = result
                        result.x.unshift("2017-01-01")
                        result.y.unshift(0)

                        var x = {}
                        x.x = result.x
                        x.y = result.y
                        x.type = 'scatter'
                        x.line = {
                            shape: "hv"
                        }
                        console.log(x)

                        var layout = {
                            xaxis: {
                                type: 'date',
                                title: 'Date',
                                tickformat: '%B %d, %Y'
                            },
                            yaxis: {
                                range: [0, Math.max(result.y) * 1.2]
                            }
                        }

                        Plotly.newPlot('graph', [x], layout)

                    })

                }

                $this.regraph()

                $scope.update = function() {
                    var input = {"count": $("#wc_number").val()};
                    WordCount.add({workID: $routeParams.workID}, input).$promise.then(
                        function(work) {
                            $scope.work = work;
                            $('#wordcount_modal').modal('hide');
                            $this.regraph
                        })
                }

            }
        ]
    });
