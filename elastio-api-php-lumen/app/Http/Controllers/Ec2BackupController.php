<?php
/*
 * Author: Robert Saylor
 * customphpdesign@gmail.com
 * www.customphpdesign.com
 */
namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\JsonResponse;
use App\Service\EapService;

class Ec2BackupController extends Controller
{
    public function ec2Backup(Request $request): \Illuminate\Http\JsonResponse
    {
        $json = $request->json()->all();
        return EapService::newEc2Backup($json);
    }

    public function ec2Restore(Request $request): \Illuminate\Http\JsonResponse
    {
        $json = $request->json()->all();
        return EapService::restoreEc2Backup($json);
    }
}
