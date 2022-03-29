<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use App\Models\ElastioBackupQueue;
use App\Service\EapService;

class PendingElastioBackupCommand extends Command
{
    protected $signature = 'command:elastio-pending-backup';
    protected $description = 'This will review any pending requests and start an Elastio EC2 backup.';

    public function __construct()
    {
        parent::__construct();
    }

    public function handle()
    {
        print "Running...";

        $data = EapService::listElastioPendingBackup();

        if (is_object($data)) {
            foreach ($data as $d) {
                print "Running backup on instance: {$d->instanceID}\n";
                ElastioBackupQueue::updateStatus($d->id, 'running');
                $cmd = "cd /home/ubuntu/ansible && bash scripts/backup_ec2.sh {$d->instanceID} {$d->id} {$d->iid}";
                system($cmd);
            }
        }
        return 1;
    }
}
