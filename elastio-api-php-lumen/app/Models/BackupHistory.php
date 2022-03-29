<?php
/*
 * Author: Robert Saylor
 * customphpdesign@gmail.com
 * www.customphpdesign.com
 */
namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class BackupHistory extends Model
{
    protected $table = "backup_history";
    protected $fillable = [
        'instanceID',
        'recovery_point',
        'created_at',
        'updated_at'
    ];
    public $timestamps = false;

    public static function recordBackupHistory($details)
    {
        if (is_object($details)) {
            foreach ($details as $d) {
                $history = new self;
                $history->instanceID = $d->iid;
                $history->recovery_point = $d->currentRecoveryID;
                $history->created_at = new \DateTime();
                $history->updated_at = new \DateTime();
                $history->save();

                return true;
            }
        }
        return false;
    }
}
