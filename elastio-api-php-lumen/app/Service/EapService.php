<?php
/*
 * Author: Robert Saylor
 * customphpdesign@gmail.com
 * www.customphpdesign.com
 */
namespace App\Service;

use Illuminate\Http\JsonResponse;
use File;

class EapService
{
    /**
     * @param $message
     * @param $code
     * @return JsonResponse
     */
    private static function sendJsonResponse($message, $code): JsonResponse
    {
        switch ($code) {
            case "200":
                $messageType = "success";
                break;
            default:
                $messageType = "errors";
                break;
        }

        if ($messageType == "errors") {
            return response()->json([
                'errors' => $message
            ], $code);
        } else {
            return response()->json([
                'meta' => [
                    $messageType => $message
                ]
            ], $code);
        }
    }

    /**
     * @param $output
     * @return false|string
     */
    private static function getJobId($output)
    {
        return strstr($output, 'j-');
    }

    /**
     * @param $output
     * @return array
     */
    private static function getRecoveryId($output): array
    {
        $recoveryID = "error";
        $code = "400";
        $line = strtok($output, PHP_EOL);
        while ($line !== FALSE) {
            $line = strtok(PHP_EOL);
            if (preg_match("/rp_id/i", $line)) {
                $temp = substr($line, 0, -1);
                $temp = str_replace('"', '', $temp);
                $temp = str_replace(' ', '', $temp);
                $arr = explode(":", $temp);
                $recoveryID = $arr[1];
                $code = "200";
            }
        }
        /* Free up memory */
        strtok('', '');

        return [
            "code" => $code,
            "recoveryID" => $recoveryID,
        ];
    }

    /**
     * @param $jobID
     * @return false|string|null
     */
    private static function monitorJob($jobID)
    {
        $cmd = "cd /home/ubuntu && sudo elastio job monitor --job-id {$jobID} 2>&1; echo $?";
        return self::runShell($cmd);
    }

    /**
     * @param $cmd
     * @return false|string|null
     */
    private static function runShell($cmd)
    {
        return shell_exec($cmd);
    }

    /**
     * @param $json
     * @return JsonResponse
     */
    public static function newEc2Backup($json): JsonResponse
    {
        $instanceID = $json['instanceID'];

        $cmd = "cd /home/ubuntu && sudo elastio ec2 backup --instance-id {$instanceID} 2>&1; echo $?";
        $output = self::runShell($cmd);

        $jobID = self::getJobId($output);

        $output = self::monitorJob($jobID);

        $status = self::getRecoveryId($output);
        return self::sendJsonResponse($status['recoveryID'], $status['code']);
    }

    public static function restoreEc2Backup($json): JsonResponse
    {
        $recoveryID = $json['recoveryID'];

        $cmd = "cd /home/ubuntu && sudo elastio ec2 restore --rp {$recoveryID} 2>&1; echo $?";
        $output = self::runShell($cmd);
        $jobID = self::getJobId($output);

        $output = self::monitorJob($jobID);

        if (preg_match("/Finish/i", $output)) {
            // success
            $code = "200";
            $message = "success";
        } else {
            $code = "400";
            $message = "error";
        }
        return self::sendJsonResponse($message, $code);
    }

    /**
     * @param $json
     * @return JsonResponse
     */
    public static function newEbsBackup($json): JsonResponse
    {
        $volumeID = $json['volumeID'];

        $cmd = "cd /home/ubuntu && sudo elastio ebs backup --volume-id {$volumeID} 2>&1; echo $?";
        $output = self::runShell($cmd);
        $jobID = self::getJobId($output);

        $output = self::monitorJob($jobID);

        $status = self::getRecoveryId($output);
        return self::sendJsonResponse($status['recoveryID'], $status['code']);
    }

    /**
     * @param $json
     * @return JsonResponse
     */
    public static function restoreEbsBackup($json): JsonResponse
    {
        $recoveryID = $json['recoveryID'];
        $cmd = "cd /home/ubuntu && sudo elastio ebs restore --rp {$recoveryID} 2>&1; echo $?";
        $output = self::runShell($cmd);

        $jobID = self::getJobId($output);

        $output = self::monitorJob($jobID);

        if (preg_match("/Finish/i", $output)) {
            // success
            $code = "200";
            $message = "success";
        } else {
            $code = "400";
            $message = "error";
        }
        return self::sendJsonResponse($message, $code);
    }

    public static function iScanRp($json)
    {
        $recoveryID = $json['recoveryID'];
        $cmd = "cd /home/ubuntu && sudo elastio iscan --background --rp {$recoveryID} 2>&1; echo $?";
        $output = self::runShell($cmd);

        $jobID = self::getJobId($output);

        $output = self::monitorJob($jobID);

        if (preg_match("/Succeeded/i", $output)) {
            // success
            $code = "200";
            $message = "success";
        } else {
            $code = "400";
            $message = "error";
        }
        return self::sendJsonResponse($message, $code);
    }

    public static function iScanFile($request)
    {
        $direcotry = "iscan_" . date("U") . "_" . rand(100,1000);
        $path = "/var/www/iscan_temp/" . $direcotry;
        @mkdir($path, $mode = 0777, false);

        $file = $request->file('iscan_file');
        $fileName = $file->getClientOriginalName();
        try {
            $file->move($path, $fileName);
        } catch (\Exception $e) {
            return self::sendJsonResponse("Unable to upload file. Error: {$e}", '400');
        }

        $cmd = "cd /home/ubuntu && sudo elastio --output-format json iscan --path {$path} 2>&1; echo $?";
        $output = self::runShell($cmd);
        $output = substr($output, 0, -2);

        $fileWithPath = $path . "/" . $fileName;
        try {
            unlink($fileWithPath);
        } catch (\Exception $e) {
            return self::sendJsonResponse("Unable to remove uploaded file. Error: {$e}", '400');
        }

        try {
            rmdir($path);
        } catch (\Exception $e) {
            return self::sendJsonResponse("Unable to remove temporary directory. Error: {$e}", '400');
        }

        $data = json_decode($output, true);
        $summary = $data['summary']['scan_summaries'][0]['summary'];

        $results = [
          'malware' => [
              'clean_files' => $summary['malware_scan']['clean'],
              'corrupted_files' => $summary['malware_scan']['corrupted'],
              'encrypted_files' => $summary['malware_scan']['encrypted'],
              'incomplete_files' => $summary['malware_scan']['incomplete'],
              'infected_files' => $summary['malware_scan']['infected'],
              'suspicious_files' => $summary['malware_scan']['suspicious'],
              'total_files' => $summary['malware_scan']['total'],
          ],
          'ransomware' => [
              'suspicious_files' => $summary['ransomware_scan']['suspicious'],
              'total_files' => $summary['ransomware_scan']['total'],
          ]
        ];

        return self::sendJsonResponse($results, '200');
    }
}
