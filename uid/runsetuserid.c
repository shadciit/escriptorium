#include <stdlib.h>
#include <unistd.h>

int main(){
  setuid(0);
  system("/home/pierre/uid/montest.py");
  return 0;
}
