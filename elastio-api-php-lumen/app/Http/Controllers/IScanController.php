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

class IScanController extends Controller
{
    public function IScanRp(Request $request)
    {
        $json = $request->json()->all();
        return EapService::iScanRp($json);
    }

    public function IscanFile(Request $request)
    {
        return EapService::iScanFile($request);
    }
}
