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

class ElastioController extends Controller
{
    public function listPending()
    {
        return EapService::listElastioPendingBackup();
    }

    public function newPending($id)
    {
        return EapService::newElastioBackup($id);
    }

    public function processPending($id)
    {
        return EapService::processElastioBackup($id);
    }
}
