#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

static char *fieldcpy(char *dst, char *fld) {
    while (*fld && *fld != ':') 
        fld++;
    if (!*(fld++)) 
        return NULL;
    while (isspace(*fld)) fld++;
    return strcpy(dst, fld);
}

static void dopkgmirrorpkgs(int argc, char *argv[]) {
    char buf[1000];
    char cur_pkg[1000];
    char cur_ver[1000];
    char cur_arch[1000];
    char cur_size[1000];
    char cur_md5[1000];
    char cur_filename[1000];
    FILE *f;

    if (argc != 4) return;

    cur_pkg[0] = cur_ver[0] = cur_arch[0] = cur_filename[0] = '\0';

    f = fopen(argv[3], "r");
    if (f == NULL) {
        perror(argv[3]);
        exit(1);
    }
    while (fgets(buf, sizeof(buf), f)) {
        if (*buf && buf[strlen(buf)-1] == '\n') buf[strlen(buf)-1] = '\0';
        if (strncasecmp(buf, "Package:", 8) == 0) {
            fieldcpy(cur_pkg, buf);
        } else if (strncasecmp(buf, "Version:", 8) == 0) {
            fieldcpy(cur_ver, buf);
        } else if (strncasecmp(buf, "Architecture:", 13) == 0) {
            fieldcpy(cur_arch, buf);
        } else if (strncasecmp(buf, "Size:", 5) == 0) {
            fieldcpy(cur_size, buf);
        } else if (strncasecmp(buf, "MD5sum:", 7) == 0) {
            fieldcpy(cur_md5, buf);
        } else if (strncasecmp(buf, "Filename:", 9) == 0) {
            fieldcpy(cur_filename, buf);
        } else if (!*buf) {
            if (strcmp(cur_pkg, argv[1]) == 0) {
                printf("%s %s %s %s %s %s %s\n", cur_pkg, cur_ver, cur_arch, argv[2], cur_filename, cur_md5, cur_size);
                exit(0);
            }
        }
    }
    /* no output indicates not found */
    exit(0);
}

static int dotranslatewgetpercent(int low, int high, int end, char *str) {
    int ch;
    int val, lastval;

    /* print out anything that looks like a % on its own line, appropriately
     * scaled */

    lastval = val = 0;
    while ( (ch = getchar()) != EOF ) {
        if (isdigit(ch)) {
	    val *= 10; val += ch - '0';
	} else if (ch == '%') {
	    float f = (float) val / 100.0 * (high - low) + low;
	    if (str) {
	    	printf("P: %d %d %s\n", (int) f, end, str);
	    } else {
	    	printf("P: %d %d\n", (int) f, end);
	    }
	    lastval = val;
	} else {
	    val = 0;
	}
    }
    return lastval == 100;
}

int main(int argc, char *argv[]) {
    if (argc == 4) {
	dopkgmirrorpkgs(argc, argv);
	exit(0);
    } else if ((argc == 6 || argc == 5) && strcmp(argv[1], "WGET%") == 0) {
	if (dotranslatewgetpercent(atoi(argv[2]), atoi(argv[3]), 
	                           atoi(argv[4]), argc == 6 ? argv[5] : NULL))
	{
	    exit(0);
	} else {
	    exit(1);
	}
    } else {
        fprintf(stderr, "usage: %s pkg mirror packages_file\n", argv[0]);
	fprintf(stderr, "   or: %s WGET%% low high end reason\n", argv[0]);
        exit(1);
    }
}
