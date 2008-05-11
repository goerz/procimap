#!/usr/bin/perl -w
use strict;

use Mail::GPG;
my $mg = Mail::GPG->new;

my $warnings = 0; # display warnings
my $mbox = 0; # input is part of a mbox file

# parse command line
foreach my $argument (@ARGV){
    $warnings = 1 if ($argument eq '-w');
    $mbox = 1 if ($argument eq '-mbox');
}

# slurp the whole message from stdin and prepare decrypted output
my $message = join('', <STDIN>);
my $firstline = '';
if ($message=~/^(.*)$/m){ $firstline = $1}
my $decrypted = '';
$decrypted = $firstline."\n" if ($mbox);

# try to decrypt
eval{

    # parse the email
    my $entity = Mail::GPG->parse(
        mail_sref => \$message
    );

    # decrypt
    my ( $decrypted_entity, $result ) = $mg->decrypt( 
        entity => $entity
    );

    if ($result->get_enc_ok){ # decryption was successfull

        # add headers
        my $headerline_decrypt = sprintf("Encrypted for %s (%s)", $result->get_enc_mail, join(',', @{$result->get_enc_key_ids}));
        my $headerline_sign = 'Message was not signed';
        if ($result->get_is_signed){
            $headerline_sign = sprintf("Signature was %s; Signed by %s (%s)", $result->get_sign_state, $result->get_sign_mail, $result->get_sign_key_id);
        }
        $decrypted_entity->head->replace('X-GPG-Decrypted', $headerline_decrypt);
        $decrypted_entity->head->replace('X-GPG-SignCheck', $headerline_sign);
        $decrypted_entity->sync_headers(Length=>'COMPUTE'); # fix the length header

        # print out
        $decrypted .= $decrypted_entity->stringify();
    } else {
        $decrypted = $message;
    }

};

if ($@){ # catch errors in eval block
    $decrypted = $message;
    warn ("Not decrypted: $@    $firstline\n\n") if ($warnings);
}

if ( (not defined($decrypted)) or ($decrypted eq '') ){ # catch if still for some reason $decrypted was not filled
    $decrypted = $message;
    warn ("Not defined or empty:\n    $firstline\n\n") if ($warnings);
}

print $decrypted;
