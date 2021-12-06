#include <sys/types.h>
#include <pwd.h>
#include <stdio.h>

int main(int argc, char **argv){

  struct passwd *userinfo;

  userinfo = getpwnam(argv[1]);
  printf("%d\n", userinfo->pw_uid);

  return 0;  

}
