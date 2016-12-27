'use strict';

angular.module('core.controllers', ['core.user'])
    .controller('userController', function($scope, User){
        $scope.user = User.query()
    })
