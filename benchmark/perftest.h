/*
 * Copyright (c) 2015 Kai Zhang (kay21s@gmail.com)
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

#ifndef _MAIN_H_
#define _MAIN_H_

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include <stdint.h>
#include <inttypes.h>
#include <sys/types.h>
#include <sys/queue.h>
#include <setjmp.h>
#include <stdarg.h>
#include <ctype.h>
#include <errno.h>
#include <getopt.h>
#include <sched.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>


#include <rte_common.h>
#include <rte_log.h>
#include <rte_memory.h>
#include <rte_memcpy.h>
#include <rte_memzone.h>
#include <rte_tailq.h>
#include <rte_eal.h>
#include <rte_per_lcore.h>
#include <rte_launch.h>
#include <rte_atomic.h>
#include <rte_cycles.h>
#include <rte_prefetch.h>
#include <rte_lcore.h>
#include <rte_per_lcore.h>
#include <rte_branch_prediction.h>
#include <rte_interrupts.h>
#include <rte_pci.h>
#include <rte_random.h>
#include <rte_debug.h>
#include <rte_ether.h>
#include <rte_ip.h>
#include <rte_udp.h>
#include <rte_ethdev.h>
#include <rte_ring.h>
#include <rte_mempool.h>
#include <rte_mbuf.h>
#include <rte_byteorder.h>



#ifdef RTE_EXEC_ENV_BAREMETAL
#define MAIN _main
#else
#define MAIN main
#endif

/* Following protocol speicific parameters should be same with MEGA */
#define PROTOCOL_MAGIC	0x1234
#define MEGA_JOB_GET 0x2
#define MEGA_JOB_SET 0x3
/* BITS_INSERT_BUF should be same with mega: config->bits_insert_buf */
#define BITS_INSERT_BUF 3 // 2^3 = 8

#define MEGA_MAGIC_NUM_LEN	2
#define MEGA_END_MARK_LEN	2

#define EIU_HEADER_LEN  42//14+20+8 = 42
#define ETHERNET_HEADER_LEN 14


/* ========== Key definitions ========== */

/* if PRELOAD is disabled, the main program should preload locally */
//#define PRELOAD		1

/* Key Distribution, only one can be enabled */
#define DIS_UNIFORM	1
//#define DIS_ZIPF	1

#if defined(DIS_ZIPF)
	#define ZIPF_THETA 0.99
	#define AFFINITY_MAX_QUEUE 1
/* Core Affinity, zipf distribution needs more cores for calculation */
	// #define NUM_QUEUE 7
#elif defined(DIS_UNIFORM)
	#define ZIPF_THETA 0.00
	#define AFFINITY_ONE_NODE 1
	// #define NUM_QUEUE 4
#endif

/* Hash Table Load Factor, These should be the same with the main program
 * if PRELOAD is disabled! TODO: avoid mismatches */
#define LOAD_FACTOR 0.2
#define PRELOAD_CNT (LOAD_FACTOR * ((1 << 30)/8))
#define TOTAL_CNT (((uint32_t)1 << 31) - 1)


// #define KEY_LEN			8
// #define VALUE_LEN		8
// #define SET_LEN		(KEY_LEN + VALUE_LEN + 8)
#define ETHERNET_MAX_FRAME_LEN	1514

/* choose which workload to use with the above parameters
 * 0 - 100% GET, 1 - 95% GET, 5% SET
 * Only supports 8 byte key/value */
int WORKLOAD_ID = 0;

/* 100%GET : 0  Set, 100Get, (42+2+2) + (12 * 122) = 1510
 * 95% GET : 5  Set, 95 Get, (42+2+2) + (24*1 + 12*19)*5 = 1306
 * 90% GET : 11 Set, 99 Get, (42+2+2) + (24*1 + 12*9)*11 = 1498
 * 80% GET : 20 Set, 80 Get, (42+2+2) + (24*1 + 12*4)*20 = 1486
 * 70% GET : 27 Set, 63 Get, (42+2+2) + (24*3 + 12*7)*9  = 1450
 * 60% GET : 34 Set, 51 Get, (42+2+2) + (24*2 + 12*3)*17 = 1474
 * 50% GET : 40 Set, 40 Get, (42+2+2) + (24*1 + 12*1)*40 = 1486
 * */
const unsigned int number_packet_set[8] = {0, 5, 11, 20, 27, 34, 40};
const unsigned int number_packet_get[8] = {122, 95, 99, 80, 63, 51, 40};
const unsigned int length_packet[8] = {1510, 1306, 1498, 1486, 1450, 1474, 1486};

/* ------------------------------------------------------- */

/* TODO: Set following values.
 * DPDK does not require MAC address to send a packet */
//#define LOCAL_MAC_ADDR
#define KV_IP_ADDR (uint32_t)(789)
#define KV_UDP_PORT (uint16_t)(124)
#define LOCAL_IP_ADDR (uint32_t)(456)
#define LOCAL_UDP_PORT (uint16_t)(123)


#define _GNU_SOURCE
#define __USE_GNU

#define MBUF_SIZE (2048 + sizeof(struct rte_mbuf) + RTE_PKTMBUF_HEADROOM)
#define NB_MBUF  2048

/*
 * RX and TX Prefetch, Host, and Write-back threshold values should be
 * carefully set for optimal performance. Consult the network
 * controller's datasheet and supporting DPDK documentation for guidance
 * on how these parameters should be set.
 */
#define RX_PTHRESH 8 /**< Default values of RX prefetch threshold reg. */
#define RX_HTHRESH 8 /**< Default values of RX host threshold reg. */
#define RX_WTHRESH 4 /**< Default values of RX write-back threshold reg. */

/*
 * These default values are optimized for use with the Intel(R) 82599 10 GbE
 * Controller and the DPDK ixgbe PMD. Consider using other values for other
 * network controllers and/or network drivers.
 */
#define TX_PTHRESH 36 /**< Default values of TX prefetch threshold reg. */
#define TX_HTHRESH 0  /**< Default values of TX host threshold reg. */
#define TX_WTHRESH 0  /**< Default values of TX write-back threshold reg. */

// #define MAX_PKT_BURST 1
#define BURST_TX_DRAIN_US 100 /* TX drain every ~100us */

/*
 * Configurable number of RX/TX ring descriptors
 */
#define RTE_TEST_RX_DESC_DEFAULT 128
#define RTE_TEST_TX_DESC_DEFAULT 512
static uint16_t nb_rxd = RTE_TEST_RX_DESC_DEFAULT;
static uint16_t nb_txd = RTE_TEST_TX_DESC_DEFAULT;

struct mbuf_table {
    unsigned len;
    struct rte_mbuf **m_table; // Need to initialize with max_packet_burst
};

#define MAX_RX_QUEUE_PER_LCORE 16
#define MAX_TX_QUEUE_PER_PORT 16
struct lcore_queue_conf {
    struct mbuf_table tx_mbufs[MAX_TX_QUEUE_PER_PORT];
} __rte_cache_aligned;
// struct lcore_queue_conf lcore_queue_conf[NUM_QUEUE];

static const struct rte_eth_conf port_conf = {
    .rxmode = {
        .mq_mode = ETH_MQ_RX_RSS,
        .max_rx_pkt_len = ETHER_MAX_LEN,
        .split_hdr_size = 0,
        .header_split   = 0, /**< Header Split disabled */
        .hw_ip_checksum = 0, /**< IP checksum offload disabled */
        .hw_vlan_filter = 0, /**< VLAN filtering disabled */
        .jumbo_frame    = 0, /**< Jumbo Frame Support disabled */
        .hw_strip_crc   = 0, /**< CRC stripped by hardware */
    },
    .rx_adv_conf = {
        .rss_conf = {
            .rss_key = NULL,
            .rss_hf = ETH_RSS_IP,
        },
    },
    .txmode = {
        .mq_mode = ETH_MQ_TX_NONE,
    },
};

static const struct rte_eth_rxconf rx_conf = {
    .rx_thresh = {
        .pthresh = RX_PTHRESH,
        .hthresh = RX_HTHRESH,
        .wthresh = RX_WTHRESH,
    },
};

static const struct rte_eth_txconf tx_conf = {
    .tx_thresh = {
        .pthresh = TX_PTHRESH,
        .hthresh = TX_HTHRESH,
        .wthresh = TX_WTHRESH,
    },
    .tx_free_thresh = 0, /* Use PMD default values */
    .tx_rs_thresh = 0, /* Use PMD default values */
    /*
     * As the example won't handle mult-segments and offload cases,
     * set the flag by default.
     */
    .txq_flags = ETH_TXQ_FLAGS_NOMULTSEGS | ETH_TXQ_FLAGS_NOOFFLOADS,
};

// #define NUM_MAX_CORE 32
/* Per-port statistics struct */
struct benchmark_core_statistics {
    uint64_t tx;
    uint64_t rx;
    uint64_t dropped;
    int enable;
} __rte_cache_aligned;

/* A tsc-based timer responsible for triggering statistics printout */
#define TIMER_MILLISECOND 2000000ULL /* around 1ms at 2 Ghz */
#define MAX_TIMER_PERIOD 86400 /* 1 day max */
static int64_t timer_period = 5 * TIMER_MILLISECOND * 1000; /* default period is 5 seconds */

struct timeval startime;
struct timeval endtime;

typedef struct context_s {
    unsigned int core_id;
    unsigned int queue_id;
} context_t;


static void print_stats();

/* Check the link status of all ports in up to 9s, and print them finally */
static void
check_all_ports_link_status(uint8_t port_num, uint32_t port_mask)
{
#define CHECK_INTERVAL 100 /* 100ms */
#define MAX_CHECK_TIME 90 /* 9s (90 * 100ms) in total */
    uint8_t portid, count, all_ports_up, print_flag = 0;
    struct rte_eth_link link;

    printf("\nChecking link status");
    fflush(stdout);
    for (count = 0; count <= MAX_CHECK_TIME; count++) {
        all_ports_up = 1;
        for (portid = 0; portid < port_num; portid++) {
            if ((port_mask & (1 << portid)) == 0)
                continue;
            memset(&link, 0, sizeof(link));
            rte_eth_link_get_nowait(portid, &link);
            /* print link status if flag set */
            if (print_flag == 1) {
                if (link.link_status)
                    printf("Port %d Link Up - speed %u "
                        "Mbps - %s\n", (uint8_t)portid,
                        (unsigned)link.link_speed,
                (link.link_duplex == ETH_LINK_FULL_DUPLEX) ?
                    ("full-duplex") : ("half-duplex\n"));
                else
                    printf("Port %d Link Down\n",
                        (uint8_t)portid);
                continue;
            }
            /* clear all_ports_up flag if any link down */
            if (link.link_status == 0) {
                all_ports_up = 0;
                break;
            }
        }
        /* after finally printing all link status, get out */
        if (print_flag == 1)
            break;

        if (all_ports_up == 0) {
            printf(".");
            fflush(stdout);
            rte_delay_ms(CHECK_INTERVAL);
        }

        /* set the print_flag if all ports up or timeout */
        if (all_ports_up == 1 || count == (MAX_CHECK_TIME - 1)) {
            print_flag = 1;
            printf("done\n");
        }
    }
}




#endif /* _MAIN_H_ */
