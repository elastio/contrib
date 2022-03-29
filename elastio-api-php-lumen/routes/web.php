<?php

/** @var \Laravel\Lumen\Routing\Router $router */

/*
|--------------------------------------------------------------------------
| Application Routes
|--------------------------------------------------------------------------
|
| Here is where you can register all of the routes for an application.
| It is a breeze. Simply tell Lumen the URIs it should respond to
| and give it the Closure to call when that URI is requested.
|
*/

$router->get('/', function () use ($router) {
    return "You do not have access.";
});

$router->group(['prefix' => 'api'], function () use ($router) {
    //$router->get('/instance', ['middleware' => 'auth', 'uses' => 'InstanceController@listInstance']);
    //$router->post('/instance', ['middleware' => 'auth', 'uses' => 'InstanceController@newInstance']);
    //$router->put('/instance/{id}', ['middleware' => 'auth', 'uses' => 'InstanceController@updateInstance']);
    //$router->delete('/instance/{id}', ['middleware' => 'auth', 'uses' => 'InstanceController@deleteInstance']);

    //$router->get('/elastio', ['middleware' => 'auth', 'uses' => 'ElastioController@listPending']);
    //$router->post('/elastio/{id}', ['middleware' => 'auth', 'uses' => 'ElastioController@newPending']);
    //$router->put('/elastio/{id}', ['middleware' => 'auth', 'uses' => 'ElastioController@processPending']);

    /* Elastio : EC2 (backup/restore) */
    $router->post('/ec2/new', ['middleware' => 'auth', 'uses' => 'Ec2BackupController@ec2Backup']);
    $router->post('/ec2/restore', ['middleware' => 'auth', 'uses' => 'Ec2BackupController@ec2Restore']);

    /* Elastio : EBS (backup/restore) */
    $router->post('/ebs/new', ['middleware' => 'auth', 'uses' => 'EbsVolumeBackupController@ebsBackup']);
    $router->post('/ebs/restore', ['middleware' => 'auth', 'uses' => 'EbsVolumeBackupController@ebsRestore']);

    /* Elastio : iscan */
    $router->post('/iscan/rp', ['middleware' => 'auth', 'uses' => 'IScanController@IScanRp']);
    $router->post('/iscan/file', ['middleware' => 'auth', 'uses' => 'IScanController@IscanFile']);

});
