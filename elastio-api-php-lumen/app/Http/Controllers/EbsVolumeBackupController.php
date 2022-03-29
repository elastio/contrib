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

class EbsVolumeBackupController extends Controller
{
    public function ebsBackup(Request $request): \Illuminate\Http\JsonResponse
    {
        $json = $request->json()->all();
        return EapService::newEbsBackup($json);
    }

    public function ebsRestore(Request $request): \Illuminate\Http\JsonResponse
    {
        $json = $request->json()->all();
        return EapService::restoreEbsBackup($json);
    }
}
