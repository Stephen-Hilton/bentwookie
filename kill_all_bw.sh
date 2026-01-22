echo "...Looking for BentWookies to kill..."
sleep 0.7

PTXT=$(ps aux | grep "bw loop" | grep -v grep)
echo $PTXT

PID=$(echo $PTXT | awk '{print $2}')
echo $PID

kill $PID
sleep 2
echo "...still alive?"
ps aux | grep "bw loop" | grep -v grep

