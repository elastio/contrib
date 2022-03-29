<?php
/*
 * Author: Robert Saylor
 * customphpdesign@gmail.com
 * www.customphpdesign.com
 */
namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\JsonResponse;
use App\Service\HistoricEapServiceEapService AS EapService;

class InstanceController extends Controller
{
    public function listInstance(Request $request)
    {
        return EapService::getInstances($request);
    }

    public function newInstance(Request $request)
    {
        $json = $request->json()->all();
        return EapService::newInstance($json);
    }

    public function updateInstance($id, Request $request)
    {
        $json = $request->json()->all();
        return EapService::updateInstance($id, $json);
    }

    public function deleteInstance($id)
    {
        return EapService::deleteInstance($id);
    }
}
