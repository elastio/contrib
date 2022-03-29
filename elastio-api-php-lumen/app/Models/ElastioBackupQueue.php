<?php
/*
 * Author: Robert Saylor
 * customphpdesign@gmail.com
 * www.customphpdesign.com
 */
namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class ElastioBackupQueue extends Model
{
    protected $table = "elastio_backup_queue";
    protected $fillable = [
        'instanceID',
        'status',
        'created_at',
        'updated_at'
    ];
    public $timestamps = false;

    public static function listPending()
    {
        $status = "pending";

        $query = self::from('elastio_backup_queue as q')
            ->select(
                'q.id',
                'q.status',
                'i.id AS iid',
                'i.instanceID'
            )
        ;

        $query->join('instances as i', function ($innerJoin) {
            $innerJoin->on('q.instanceID', '=', 'i.id');
        });

        $query->where(function ($filter) use ($status) {
           $filter->where('q.status', '=', $status);
        });

        return $query->get();
    }

    public static function newBackup($id)
    {
        $backup = new self;
        $backup->instanceID = $id;
        $backup->status = "pending";
        $backup->created_at = new \DateTime();
        $backup->updated_at = new \DateTime();
        $backup->save();

        return true;
    }

    public static function updateStatus($id, $status)
    {
        $backup = self::find($id);
        $backup->status = $status;
        $backup->save();

        return true;
    }

    public static function getParentDetails($id)
    {
        $query = self::from('elastio_backup_queue as q')
            ->select(
                'q.id',
                'q.status',
                'i.id AS iid',
                'i.instanceID',
                'i.currentRecoveryID'
            )
        ;

        $query->join('instances as i', function ($innerJoin) {
            $innerJoin->on('q.instanceID', '=', 'i.id');
        });

        $query->where(function ($filter) use ($id) {
            $filter->where('q.id', '=', $id);
        });

        return $query->get();
    }
}
