<?php
/*
 * Author: Robert Saylor
 * customphpdesign@gmail.com
 * www.customphpdesign.com
 */
namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Instances extends Model
{
    protected $table = "instances";
    protected $fillable = [
        'name',
        'instanceID',
        'active',
        'currentRecoveryID',
        'date_created',
        'date_updated'
    ];
    public $timestamps = false;

    public static function getInstances()
    {
        $query = self::from('instances as i')
            ->select(
                'i.id',
                'i.name',
                'i.instanceID',
                'i.active',
                'i.currentRecoveryID',
                'i.date_created',
                'i.date_updated'
            )
        ;

        $query->where(function ($filter) {
            $filter->where('i.active', '=', true);
        });

        $total = $query->count();

        $result = $query->get();

        return
            [
                'meta' => [
                    'total' => $total
                ],
                'data' => $result,
            ];
    }

    public static function newInstances($json)
    {
        $instance = new self;
        $instance->name = $json['name'];
        $instance->instanceID = $json['instanceID'];
        $instance->active = $json['active'];
        $instance->date_created = new \DateTime();
        $instance->date_updated = new \DateTime();
        $instance->save();

        return true;
    }

    public static function updateInstance($id, $json)
    {
        $instance = self::find($id);
        if (isset($json['name'])) {
            $instance->name = $json['name'];
        }
        if (isset($json['instanceID'])) {
            $instance->instanceID = $json['instanceID'];
        }
        if (isset($json['active'])) {
            $instance->active = $json['active'];
        }
        if (isset($json['currentRecoveryID'])) {
            $instance->currentRecoveryID = $json['currentRecoveryID'];
        }
        $instance->date_updated = new \DateTime();
        $instance->save();

        return true;
    }

    public static function deleteInstance($id)
    {
        $instance = self::find($id);
        $instance->active = false;
        $instance->save();

        return true;
    }
}
