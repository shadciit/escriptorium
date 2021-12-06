#include <unistd.h>
#include <stdio.h>

int main(){
  uid_t uid = getuid();
  uid_t euid = geteuid();

  printf("uid : %d\n", uid);
  printf("euid : %d\n", euid);

  setuid(20);

  uid = getuid();
  euid = geteuid();

  printf("uid : %d\n", uid);
  printf("euid : %d\n", euid);
}
