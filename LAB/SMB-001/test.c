#include <libsmbclient.h>
#include <stdio.h>

#include <string.h>

static void get_auth(const char *srv, const char *shr, char *wg, int wglen,
                     char *un, int unlen, char *pw, int pwlen)
{
    // Kerberos: leave username/password empty
    if (un && unlen > 0) un[0] = '\0';
    if (pw && pwlen > 0) pw[0] = '\0';
}

int main() {
    // Initialize SMB client with auth callback
    if (smbc_init(get_auth, 0) < 0) {
        perror("smbc_init");
        return 1;
    }

    SMBCCTX *ctx = smbc_new_context();
    if (!ctx) {
        fprintf(stderr, "Failed to create SMBC context\n");
        return 1;
    }

    // Enable Kerberos authentication
    smbc_setOptionUseKerberos(ctx, 1);

    if (!smbc_init_context(ctx)) {
        fprintf(stderr, "Failed to init SMB context\n");
        return 1;
    }
    smbc_set_context(ctx);

    // Open the directory
    int dirh = smbc_opendir("smb://SMB.SRJCIPDVFS10101.PETROBRAS.BIZ/servico_002$");
    if (dirh < 0) {
        perror("smbc_opendir");
        return 1;
    }

    struct smbc_dirent *entry;
    while ((entry = smbc_readdir(dirh)) != NULL) {
        printf("%s\n", entry->name);
    }

    smbc_closedir(dirh);
    return 0;
}
